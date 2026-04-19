"""Streaming STT via Sarvam WebSocket (Saaras v3), 16 kHz mono PCM in WAV payloads."""

import asyncio
import base64
import json
import logging
import struct
import urllib.parse
from typing import Any, Dict, Optional, Callable

import websockets

from phase6_voice.config import get_voice_settings

logger = logging.getLogger(__name__)

STT_URI_BASE = "wss://api.sarvam.ai/speech-to-text/ws"

_STT_SEND_TIMEOUT_S = 15.0
_STT_RECV_AFTER_CLOSE_S = 1.0
_STT_RECV_OPEN_IDLE_S = 5.0
_STT_UTTERANCE_DEADLINE_S = 60.0


def _pcm_s16le_to_wav_bytes(pcm: bytes, sample_rate: int) -> bytes:
    """Sarvam accepts encoding=audio/wav; each payload must be a valid WAV (header + PCM)."""
    n = len(pcm)
    if n == 0:
        return b""
    byte_rate = sample_rate * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + n,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        byte_rate,
        2,
        16,
        b"data",
        n,
    )
    return header + pcm


def _stt_connect_uri() -> str:
    cfg = get_voice_settings()
    params = {
        "language-code": cfg["language"],
        "model": cfg["stt_model"],
        "mode": "transcribe",
        "sample_rate": str(cfg["sample_rate"]),
        "high_vad_sensitivity": "true",
        "vad_signals": "true",
        "flush_signal": "true",
        # Payload uses RIFF WAV (encoding audio/wav); Sarvam accepts `wav` or raw PCM codecs.
        "input_audio_codec": "wav",
    }
    return f"{STT_URI_BASE}?{urllib.parse.urlencode(params)}"


async def collect_utterance_transcript(
    api_key: str,
    pcm_queue: asyncio.Queue,
    hangup: asyncio.Event,
    *,
    use_server_vad: bool = False,
    on_transcript: Optional[Callable[[str], Any]] = None,
) -> str:
    """Forward microphone PCM to Sarvam until utterance is closed, then return transcript.

    When use_server_vad is False (push-to-talk), only the client's flush after ``utterance_end``
    ends the turn; Sarvam END_SPEECH events are ignored so silence does not cut the user off early.
    """
    uri = _stt_connect_uri()
    cfg = get_voice_settings()
    headers = [("Api-Subscription-Key", api_key)]

    state: Dict[str, Any] = {
        "transcript": "",
        "end_speech": False,
        "utterance_closed": False,
    }
    done = asyncio.Event()

    async def receiver(ws: websockets.WebSocketClientProtocol) -> None:
        try:
            while not done.is_set():
                try:
                    # If the sender just signaled closed, we definitely don't want to wait 
                    # for the full normal idle timeout.
                    recv_to = (
                        _STT_RECV_AFTER_CLOSE_S
                        if state["utterance_closed"]
                        else 2.0  # Check in small bursts to stay responsive to flag changes
                    )
                    raw = await asyncio.wait_for(ws.recv(), timeout=recv_to)
                except asyncio.TimeoutError:
                    if state["utterance_closed"]:
                        logger.debug("STT: no more server messages after flush; finishing receiver")
                        break
                    # If not closed yet, loop back and check state["utterance_closed"] again
                    continue

                msg = json.loads(raw)
                mtype = msg.get("type")
                data = msg.get("data") or {}

                if mtype == "error":
                    err = data.get("error") or data.get("message") or str(data)
                    logger.error("Sarvam STT server error: %s", msg)
                    raise RuntimeError(f"Sarvam STT Error: {err}")

                if mtype == "events":
                    if data.get("signal_type") == "END_SPEECH":
                        state["end_speech"] = True
                        if use_server_vad and state["transcript"]:
                            done.set()

                if mtype == "data":
                    tr = (data.get("transcript") or "").strip()
                    if tr:
                        logger.debug("STT: received chunk: %s", tr)
                        # Sarvam Saaras v3 streaming behavior: 
                        # Usually, if we get non-overlapping segments, we should append.
                        # However, some implementations return cumulative results.
                        # Rule of thumb: if it's a very small delta that doesn't start with 
                        # current transcript, it's likely a new segment.
                        current = state["transcript"]
                        if not current:
                            state["transcript"] = tr
                        elif tr.startswith(current):
                            # It's cumulative, update to the longer one
                            state["transcript"] = tr
                        elif current.endswith(tr):
                            # It's already in there
                            pass
                        else:
                            # Likely a new segment or incremental update
                            state["transcript"] = f"{current} {tr}"
                        
                        # EMIT PARTIAL RESULT
                        if on_transcript:
                            try:
                                # Run callback in event loop if it's async or thread it?
                                # Simplified: assume WS handler provided a fast non-blocking relay.
                                # Check if it's awaitable.
                                if asyncio.iscoroutinefunction(on_transcript):
                                    await on_transcript(state["transcript"])
                                else:
                                    on_transcript(state["transcript"])
                            except Exception as e:
                                logger.error("STT: error in transcript callback: %s", e)

                        if use_server_vad and state["end_speech"]:
                            done.set()
        except websockets.ConnectionClosed:
            logger.debug("STT: WebSocket connection closed gracefully")
        except Exception as e:
            logger.error("STT: receiver encountered error: %s", e)
        finally:
            done.set()

    async def sender(ws: websockets.WebSocketClientProtocol) -> None:
        try:
            while not hangup.is_set() and not done.is_set():
                try:
                    chunk = await asyncio.wait_for(pcm_queue.get(), timeout=0.2)
                except asyncio.TimeoutError:
                    continue
                if chunk is None:
                    logger.debug("STT: client signaled utterance end, sending flush")
                    state["utterance_closed"] = True
                    try:
                        await asyncio.wait_for(
                            ws.send(json.dumps({"type": "flush"})),
                            timeout=_STT_SEND_TIMEOUT_S,
                        )
                    except Exception as e:
                        logger.error("STT: flush send failed: %s", e)
                    
                    # We do NOT done.set() here, we let the receiver drain naturally.
                    break
                
                wav_bytes = _pcm_s16le_to_wav_bytes(chunk, int(cfg["sample_rate"]))
                payload = {
                    "audio": {
                        "data": base64.b64encode(wav_bytes).decode("ascii"),
                        "sample_rate": int(cfg["sample_rate"]),
                        "encoding": "audio/wav",
                    }
                }
                try:
                    await asyncio.wait_for(
                        ws.send(json.dumps(payload)), timeout=_STT_SEND_TIMEOUT_S
                    )
                except Exception as e:
                    logger.error("STT: send failed: %s", e)
                    break
        finally:
            if not state["utterance_closed"]:
                try:
                    await ws.send(json.dumps({"type": "flush"}))
                except:
                    pass
            # Don't done.set() here; let receiver finish the transcript collection.

    try:
        async with websockets.connect(
            uri,
            additional_headers=headers,
            max_size=None,
            ping_interval=20,
            ping_timeout=20,
        ) as ws:
            recv_task = asyncio.create_task(receiver(ws))
            send_task = asyncio.create_task(sender(ws))
            try:
                await asyncio.wait_for(
                    done.wait(), timeout=_STT_UTTERANCE_DEADLINE_S
                )
            except asyncio.TimeoutError:
                logger.warning("STT: timed out waiting for transcript")
            finally:
                send_task.cancel()
                try:
                    await send_task
                except asyncio.CancelledError:
                    pass
                recv_task.cancel()
                try:
                    await recv_task
                except asyncio.CancelledError:
                    pass
    except Exception:
        logger.exception("STT session failed")
        return ""

    return state["transcript"].strip()
