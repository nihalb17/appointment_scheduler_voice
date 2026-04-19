"""WebSocket voice session: half-duplex streaming STT/TTS with existing orchestrator."""

import asyncio
import base64
import logging
import time
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from phase1_intent_detection_routing.orchestrator import handle_message

from phase6_voice.config import get_sarvam_api_key, get_voice_settings
from phase6_voice.sarvam_stt import collect_utterance_transcript
from phase6_voice.sarvam_tts import stream_tts_utterance
from phase6_voice.voice_orchestration import resolve_voice_turn
import random

logger = logging.getLogger(__name__)

# ~1s of 16 kHz mono s16le before forwarding to STT (fewer WS sends to Sarvam).
_PCM_COALESCE_BYTES = 32_000

# Spoken welcome aligned with chat copy (no emoji for TTS).
WELCOME_TEXT = (
    "Hi there! I'm your appointment assistant. I can help you book or cancel appointments. "
    "What would you like to do?"
)

FILLER_PHRASES = [
    "One moment.",
    "Just a second.",
    "Let me check.",
    "Looking into it.",
    "Searching now.",
]


class VoiceStop(Exception):
    """User ended the session or disconnected."""


def _drain_stale_mic_commands(cmd_q: asyncio.Queue) -> None:
    """Drop any buffered mic frames or stale UI signals from an earlier turn."""
    rest: list = []
    stale_types = {"pcm_chunk", "recording_start", "utterance_end"}
    while True:
        try:
            m = cmd_q.get_nowait()
        except asyncio.QueueEmpty:
            break
        if isinstance(m, dict) and m.get("type") in stale_types:
            continue
        rest.append(m)
    for m in rest:
        cmd_q.put_nowait(m)


async def _pump_client_json(websocket: WebSocket, cmd_q: asyncio.Queue) -> None:
    try:
        while True:
            msg: Dict[str, Any] = await websocket.receive_json()
            await cmd_q.put(msg)
    except WebSocketDisconnect:
        await cmd_q.put({"type": "_disconnect"})
    except Exception:
        logger.exception("voice pump failed")
        await cmd_q.put({"type": "_disconnect"})


async def _wait_begin_on_socket(websocket: WebSocket) -> None:
    """Read until `begin` without a background pump (avoids recv/send races on the same socket)."""
    try:
        while True:
            msg: Dict[str, Any] = await websocket.receive_json()
            t = msg.get("type")
            if t == "begin":
                return
            if t in ("hangup",):
                raise VoiceStop()
    except WebSocketDisconnect:
        raise VoiceStop()


async def _consume_listen_pcm(
    cmd_q: asyncio.Queue, pcm_queue: asyncio.Queue, hangup: asyncio.Event
) -> None:
    forward_pcm = True
    buf = bytearray()

    async def _flush_buf() -> None:
        nonlocal buf
        if buf:
            await pcm_queue.put(bytes(buf))
            buf = bytearray()

    try:
        # Push-to-talk: ignore mic data until the client signals recording_start.
        while not hangup.is_set():
            m = await cmd_q.get()
            t = m.get("type")
            if t == "recording_start":
                break
            if t == "utterance_end":
                await pcm_queue.put(None)
                return
            if t in ("hangup", "_disconnect"):
                hangup.set()
                return
            if t == "pcm_chunk":
                continue
        while not hangup.is_set():
            m = await cmd_q.get()
            t = m.get("type")
            if t == "pcm_chunk":
                raw = m.get("b64")
                if forward_pcm and raw:
                    buf.extend(base64.b64decode(raw))
                    while len(buf) >= _PCM_COALESCE_BYTES:
                        chunk = bytes(buf[:_PCM_COALESCE_BYTES])
                        del buf[:_PCM_COALESCE_BYTES]
                        await pcm_queue.put(chunk)
            elif t == "utterance_end":
                await _flush_buf()
                if forward_pcm:
                    await pcm_queue.put(None)
                return
            elif t in ("hangup", "_disconnect"):
                hangup.set()
                return
            else:
                continue
    except asyncio.CancelledError:
        raise


async def handle_voice_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id = (websocket.query_params.get("session_id") or "").strip()
    if not session_id:
        await websocket.send_json({"type": "error", "message": "session_id is required"})
        await websocket.close(code=4400)
        return

    try:
        api_key = get_sarvam_api_key()
    except RuntimeError as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close(code=4401)
        return

    hangup = asyncio.Event()
    cmd_q: asyncio.Queue = asyncio.Queue()
    # Unbounded: a bounded queue lets the mic pump block when Sarvam send() stalls,
    # which traps utterance_end behind hundreds of chunks and looks like "listening forever".
    pcm_queue: asyncio.Queue = asyncio.Queue()
    pump: Optional[asyncio.Task] = None

    async def start_pump() -> None:
        nonlocal pump
        if pump is None or pump.done():
            pump = asyncio.create_task(_pump_client_json(websocket, cmd_q))

    async def stop_pump() -> None:
        nonlocal pump
        if pump is not None:
            pump.cancel()
            try:
                await pump
            except asyncio.CancelledError:
                pass
            pump = None

    try:
        await _wait_begin_on_socket(websocket)

        cfg = get_voice_settings()
        ok = await stream_tts_utterance(
            websocket, api_key, WELCOME_TEXT, hangup, 
            stream=cfg.get("ui_streaming_enabled", True)
        )
        if not ok:
            raise VoiceStop()
        await start_pump()
        await websocket.send_json({"type": "tts_done"})

        if hangup.is_set():
            raise VoiceStop()

        while not hangup.is_set():
            _drain_stale_mic_commands(cmd_q)
            await websocket.send_json({"type": "phase", "phase": "listening"})

            listen_task = asyncio.create_task(
                _consume_listen_pcm(cmd_q, pcm_queue, hangup)
            )
            async def _on_transcript(text: str) -> None:
                if text.strip():
                    await websocket.send_json(
                        {"type": "user_transcript", "text": text.strip(), "partial": True}
                    )

            try:
                user_text = await collect_utterance_transcript(
                    api_key, pcm_queue, hangup, use_server_vad=False, on_transcript=_on_transcript
                )
            finally:
                listen_task.cancel()
                try:
                    await listen_task
                except asyncio.CancelledError:
                    pass
                _drain_stale_mic_commands(cmd_q)
                while not pcm_queue.empty():
                    try:
                        pcm_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

            if hangup.is_set():
                break

            if not (user_text or "").strip():
                await stop_pump()
                # Brief stabilization delay to ensure client-side state is reset
                await asyncio.sleep(0.5)
                ok = await stream_tts_utterance(
                    websocket,
                    api_key,
                    "Sorry, I did not catch that. Could you please repeat?",
                    hangup,
                    stream=cfg.get("ui_streaming_enabled", True)
                )
                if not ok:
                    raise VoiceStop()
                await start_pump()
                await websocket.send_json({"type": "tts_done"})
                # Extra delay after tts_done to prevent immediate re-entry before user reacts
                await asyncio.sleep(0.5)
                continue

            await websocket.send_json(
                {"type": "user_transcript", "text": user_text.strip()}
            )
            await websocket.send_json({"type": "phase", "phase": "processing"})
            
            # Start a delayed filler task if enabled
            cfg = get_voice_settings()
            filler_task = None
            if cfg.get("fillers_enabled"):
                logger.info("Fillers are ENABLED. Starting 0.3s delayed timer task.")
                async def _delayed_filler():
                    try:
                        await asyncio.sleep(0.3)  # Even faster delay to ensure it catches 'thinking' pauses
                        filler = random.choice(FILLER_PHRASES)
                        logger.info(f"0.3s timer done. Triggering voice-only delayed filler: {filler}")
                        # Fillers are now voice-only (include_caption=False)
                        await stream_tts_utterance(
                            websocket, api_key, filler, hangup,
                            stream=cfg.get("ui_streaming_enabled", True),
                            include_caption=False
                        )
                    except asyncio.CancelledError:
                        logger.info("Filler task was CANCELLED because the agent responded fast.")
                        raise

                filler_task = asyncio.create_task(_delayed_filler())
            else:
                logger.info("Fillers are DISABLED via config.")

            t0 = time.monotonic()
            try:
                # Both calls do blocking network I/O (Groq LLM, Google Calendar/Docs).
                # Running them on the event loop freezes the WS for 5-15s and causes
                # "stuck" UI on confirmation turns. Offload to a worker thread so the
                # socket stays responsive to pings and the pump can keep running.
                result = await asyncio.to_thread(
                    handle_message, session_id, user_text.strip()
                )
                t1 = time.monotonic()
                reply, ended, payload = await asyncio.to_thread(
                    resolve_voice_turn, session_id, result
                )
                t2 = time.monotonic()
                logger.info(
                    "voice turn: handle_message=%.2fs resolve_voice_turn=%.2fs total=%.2fs",
                    t1 - t0,
                    t2 - t1,
                    t2 - t0,
                )
            finally:
                if filler_task:
                    filler_task.cancel()
                    try:
                        await filler_task
                    except asyncio.CancelledError:
                        pass

            await stop_pump()
            # Sent before TTS so the client can finish playback, then apply banner / teardown.
            if ended and payload:
                try:
                    await websocket.send_json({"type": "call_ended", **payload})
                except Exception:
                    raise VoiceStop()
            ok = await stream_tts_utterance(
                websocket, api_key, reply, hangup,
                stream=cfg.get("ui_streaming_enabled", True)
            )
            if not ok:
                raise VoiceStop()
            try:
                await start_pump()
                await websocket.send_json({"type": "tts_done"})
            except Exception:
                raise VoiceStop()

            if ended and payload:
                break

    except VoiceStop:
        pass
    except Exception:
        logger.exception("voice session error")
        try:
            await websocket.send_json(
                {"type": "error", "message": "Voice session failed. Please try again."}
            )
        except Exception:
            pass
    finally:
        hangup.set()
        if pump is not None:
            pump.cancel()
            try:
                await pump
            except asyncio.CancelledError:
                pass
        try:
            await websocket.close()
        except Exception:
            pass
