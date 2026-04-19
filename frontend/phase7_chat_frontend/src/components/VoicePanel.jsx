import { useRef, useState, useEffect, useCallback } from "react";
import { voiceWebSocketUrl } from "../services/api";
import "./VoicePanel.css";

function floatTo16BitPCM(f32) {
  const out = new Int16Array(f32.length);
  for (let i = 0; i < f32.length; i++) {
    const s = Math.max(-1, Math.min(1, f32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

function downsample(f32, inRate, outRate) {
  if (inRate === outRate) return f32;
  const ratio = inRate / outRate;
  const n = Math.max(1, Math.floor(f32.length / ratio));
  const o = new Float32Array(n);
  for (let i = 0; i < n; i++) o[i] = f32[Math.min(Math.floor(i * ratio), f32.length - 1)] || 0;
  return o;
}

function i16ToB64(i16) {
  const u8 = new Uint8Array(i16.buffer);
  let bin = "";
  for (let i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
  return btoa(bin);
}

const RECORDING_MAX_MS = 120_000;

/**
 * Push-to-talk voice footer: connects when mounted (voice mode on), plays welcome TTS from server,
 * then tap mic to start / tap again to stop and send audio to the agent.
 */
export default function VoicePanel({
  disabled = false,
  onUserTranscript,
  onAssistantMessage,
  onVoiceCallComplete,
}) {
  const [phase, setPhase] = useState("connecting");
  const [hint, setHint] = useState("");
  const [recordMs, setRecordMs] = useState(0);
  const [liveTranscript, setLiveTranscript] = useState("");

  const wsRef = useRef(null);
  const recordingRef = useRef(false);
  const skipWelcomeCaptionRef = useRef(true);
  const sessionDoneRef = useRef(false);
  const pendingCallEndRef = useRef(null);
  const audioCtxRef = useRef(null);
  const micNodesRef = useRef(null);
  const recordTickRef = useRef(null);
  const recordStartRef = useRef(null);
  const maxRecordTimerRef = useRef(null);
  const inboundChainRef = useRef(Promise.resolve());
  const onMessageRef = useRef(null);
  const audioElRef = useRef(null);
  const ttsChunksRef = useRef([]);
  const ttsContentTypeRef = useRef("audio/mpeg");
  const activeBlobUrlRef = useRef(null);

  const stopMic = useCallback(() => {
    if (maxRecordTimerRef.current != null) {
      clearTimeout(maxRecordTimerRef.current);
      maxRecordTimerRef.current = null;
    }
    recordingRef.current = false;
    const nodes = micNodesRef.current;
    if (nodes) {
      try {
        nodes.proc.disconnect();
        nodes.src.disconnect();
        nodes.stream.getTracks().forEach((t) => t.stop());
      } catch (_) {}
      micNodesRef.current = null;
    }
    if (recordTickRef.current != null) {
      clearInterval(recordTickRef.current);
      recordTickRef.current = null;
    }
    recordStartRef.current = null;
    setRecordMs(0);
    // Do not clear liveTranscript here; wait for final transcript or new turn
  }, []);

  const teardownAudio = useCallback(() => {
    stopMic();
    if (audioElRef.current) {
      audioElRef.current.pause();
      audioElRef.current.src = "";
    }
    if (activeBlobUrlRef.current) {
      URL.revokeObjectURL(activeBlobUrlRef.current);
      activeBlobUrlRef.current = null;
    }
    ttsChunksRef.current = [];
    ttsContentTypeRef.current = "audio/mpeg";
    try {
      audioCtxRef.current?.close();
    } catch (_) {}
    audioCtxRef.current = null;
  }, [stopMic]);

  const ensureAudioCtx = useCallback(() => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new AudioContext();
    }
    return audioCtxRef.current;
  }, []);

  const base64ToUint8 = useCallback((b64) => {
    const raw = atob(b64);
    const u8 = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) u8[i] = raw.charCodeAt(i);
    return u8;
  }, []);

  const playBufferedTtsAndWait = useCallback(async () => {
    const el = audioElRef.current;
    if (!el) return;
    if (ttsChunksRef.current.length === 0) return;

    const chunkBytes = ttsChunksRef.current.map(base64ToUint8);
    const blob = new Blob(chunkBytes, { type: ttsContentTypeRef.current || "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    if (activeBlobUrlRef.current) {
      URL.revokeObjectURL(activeBlobUrlRef.current);
    }
    activeBlobUrlRef.current = url;
    el.src = url;
    ttsChunksRef.current = [];

    try {
      await el.play();
      await new Promise((resolve) => {
        el.onended = () => resolve();
      });
    } catch {
      if (activeBlobUrlRef.current) {
        URL.revokeObjectURL(activeBlobUrlRef.current);
        activeBlobUrlRef.current = null;
      }
      el.src = "";
      setHint("Audio blocked by browser. Please allow autoplay and try again.");
    } finally {
      el.onended = null;
      el.src = "";
    }
  }, [base64ToUint8]);

  const startMic = useCallback(
    async (ws) => {
      stopMic();
      setLiveTranscript("");
      try {
        ws.send(JSON.stringify({ type: "recording_start" }));
      } catch (_) {}
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true },
        });
      } catch {
        try {
          ws.send(JSON.stringify({ type: "utterance_end" }));
        } catch (_) {}
        throw new Error("microphone denied");
      }
      const ctx = ensureAudioCtx();
      await ctx.resume();
      const src = ctx.createMediaStreamSource(stream);
      const proc = ctx.createScriptProcessor(4096, 1, 1);
      const mute = ctx.createGain();
      mute.gain.value = 0;
      proc.onaudioprocess = (e) => {
        if (!recordingRef.current || !ws || ws.readyState !== WebSocket.OPEN) return;
        const input = e.inputBuffer.getChannelData(0);
        const down = downsample(input, ctx.sampleRate, 16000);
        const pcm = floatTo16BitPCM(down);
        try {
          ws.send(JSON.stringify({ type: "pcm_chunk", b64: i16ToB64(pcm) }));
        } catch (_) {}
      };
      src.connect(proc);
      proc.connect(mute);
      mute.connect(ctx.destination);
      micNodesRef.current = { proc, src, stream };
      recordingRef.current = true;
      recordStartRef.current = Date.now();
      setRecordMs(0);
      recordTickRef.current = setInterval(() => {
        if (recordStartRef.current) {
          setRecordMs(Date.now() - recordStartRef.current);
        }
      }, 100);
      maxRecordTimerRef.current = setTimeout(() => {
        if (!recordingRef.current) return;
        const sock = wsRef.current;
        stopMic();
        if (sock && sock.readyState === WebSocket.OPEN) {
          try {
            sock.send(JSON.stringify({ type: "utterance_end" }));
          } catch (_) {}
        }
        setPhase("processing");
        setHint("");
      }, RECORDING_MAX_MS);
    },
    [ensureAudioCtx, stopMic]
  );

  const finishRecordingTurn = useCallback(() => {
    const ws = wsRef.current;
    stopMic();
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ type: "utterance_end" }));
      } catch (_) {}
    }
    setPhase("processing");
    setHint("");
  }, [stopMic]);

  const closeWs = useCallback(() => {
    stopMic();
    const w = wsRef.current;
    wsRef.current = null;
    if (w && w.readyState === WebSocket.OPEN) {
      try {
        w.send(JSON.stringify({ type: "hangup" }));
      } catch (_) {}
      w.close();
    }
  }, [stopMic]);

  const handleMessage = useCallback(
    async (ev) => {
      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      const t = msg.type;
      if (t === "error") {
        setHint(msg.message || "Error");
        setPhase("error");
        stopMic();
        const w = wsRef.current;
        wsRef.current = null;
        if (w) {
          try {
            w.close();
          } catch (_) {}
        }
        return;
      }
      if (t === "user_transcript") {
        const text = (msg.text || "").trim();
        if (text) {
          if (msg.partial) {
            setLiveTranscript(text);
          } else {
            setLiveTranscript("");
            onUserTranscript?.(text);
          }
        }
        return;
      }
      if (t === "agent_caption") {
        ttsChunksRef.current = [];
        ttsContentTypeRef.current = "audio/mpeg";
        if (audioElRef.current) {
          audioElRef.current.pause();
          audioElRef.current.src = "";
        }
        if (activeBlobUrlRef.current) {
          URL.revokeObjectURL(activeBlobUrlRef.current);
          activeBlobUrlRef.current = null;
        }
        const text = (msg.text || "").trim();
        if (text) {
          if (skipWelcomeCaptionRef.current) {
            skipWelcomeCaptionRef.current = false;
          } else {
            onAssistantMessage?.(text, msg.stream);
          }
        }
        setPhase("speaking");
        setHint("");
        return;
      }
      if (t === "tts_audio") {
        ttsChunksRef.current.push(msg.b64);
        ttsContentTypeRef.current = msg.content_type || "audio/mpeg";
        return;
      }
      if (t === "tts_done") {
        await playBufferedTtsAndWait();
        if (sessionDoneRef.current) return;
        const pending = pendingCallEndRef.current;
        if (pending) {
          pendingCallEndRef.current = null;
          sessionDoneRef.current = true;
          onVoiceCallComplete?.(pending);
          setPhase("ended");
          setHint("");
          closeWs();
          return;
        }
        setHint("Tap to talk");
        setPhase("ready");
        return;
      }
      if (t === "phase") {
        if (msg.phase === "processing") {
          stopMic();
          setHint("");
          setPhase("processing");
        }
        if (msg.phase === "listening") {
          /* Server signals listen window; push-to-talk ignores until user taps. */
        }
        return;
      }
      if (t === "call_ended") {
        stopMic();
        pendingCallEndRef.current = {
          action: msg.action,
          headline: msg.headline || "CALL ENDED",
          message: msg.message || "",
          booking_code: msg.booking_code,
          scheduled_display: msg.scheduled_display,
          banner_text: msg.banner_text,
        };
      }
    },
    [playBufferedTtsAndWait, stopMic, closeWs, onUserTranscript, onAssistantMessage, onVoiceCallComplete]
  );

  onMessageRef.current = handleMessage;

  useEffect(() => {
    if (disabled) {
      closeWs();
      teardownAudio();
      setPhase("ended");
      return;
    }

    /** Avoid treating Strict Mode teardown (or route unmount) as a real failure. */
    const teardownRef = { current: false };

    sessionDoneRef.current = false;
    pendingCallEndRef.current = null;
    skipWelcomeCaptionRef.current = true;
    setPhase("connecting");
    setHint("Connecting…");

    const url = voiceWebSocketUrl();
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      if (teardownRef.current || wsRef.current !== ws) return;
      const fn = onMessageRef.current;
      if (!fn) return;
      inboundChainRef.current = inboundChainRef.current
        .then(() => fn(ev))
        .catch(() => {});
    };
    ws.onerror = () => {
      if (teardownRef.current) return;
      if (wsRef.current !== ws) return;
      setHint("Connection error. Is the backend running (port 8020 by default)?");
      setPhase("error");
      wsRef.current = null;
      stopMic();
    };
    ws.onclose = () => {
      if (teardownRef.current) return;
      if (wsRef.current !== ws) return;
      wsRef.current = null;
      stopMic();
    };
    ws.onopen = () => {
      if (teardownRef.current || wsRef.current !== ws) return;
      try {
        ws.send(JSON.stringify({ type: "begin" }));
      } catch (_) {}
    };

    return () => {
      teardownRef.current = true;
      inboundChainRef.current = Promise.resolve();
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        try {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "hangup" }));
          }
        } catch (_) {}
        ws.close();
      }
      stopMic();
      teardownAudio();
    };
  }, [disabled, closeWs, stopMic, teardownAudio]);

  const onPttClick = async () => {
    if (disabled || phase === "ended" || phase === "error" || phase === "connecting") return;
    if (phase === "speaking" || phase === "processing") return;

    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setHint("Reconnecting…");
      return;
    }

    if (phase === "ready") {
      try {
        await startMic(ws);
        setPhase("recording");
        setHint("Tap to stop");
      } catch {
        setHint("Microphone permission required");
      }
      return;
    }

    if (phase === "recording") {
      finishRecordingTurn();
    }
  };

  const recordSec = Math.floor(recordMs / 1000);
  const mm = String(Math.floor(recordSec / 60)).padStart(2, "0");
  const ss = String(recordSec % 60).padStart(2, "0");

  const micDisabled =
    disabled ||
    phase === "connecting" ||
    phase === "speaking" ||
    phase === "processing" ||
    phase === "ended" ||
    phase === "error";

  return (
    <div className="voice-footer">
      <audio ref={audioElRef} hidden />

      {phase === "recording" || liveTranscript ? (
        <div className="voice-live-container">
          <div className="voice-rec-timer" aria-live="polite">
            {phase === "recording" ? `Listening ${mm}:${ss}` : "Processing..."}
          </div>
          {liveTranscript && (
            <div className="voice-live-transcript">
              “{liveTranscript}”
            </div>
          )}
        </div>
      ) : (
        <div className={`voice-footer-hint ${phase === "ready" ? "voice-footer-hint-ready" : ""}`}>
          {hint ||
            (phase === "ready"
              ? "Tap to talk"
              : phase === "connecting"
                ? "Connecting…"
                : phase === "processing"
                ? "Agent is thinking..."
                : phase === "ended"
                  ? ""
                  : "")}
        </div>
      )}

      {phase === "processing" && !liveTranscript && (
        <div className="voice-processing-spinner">
          <div className="dot-pulse"></div>
        </div>
      )}

      {!disabled && (
        <div className="voice-footer-mic-row">
          <button
            type="button"
            className={`voice-ptt ${phase === "recording" ? "voice-ptt-recording" : ""} ${
              phase === "processing" ? "voice-ptt-processing" : ""
            } ${
              micDisabled ? "voice-ptt-disabled" : ""
            }`}
            onClick={onPttClick}
            disabled={micDisabled}
            aria-label={phase === "recording" ? "Stop recording" : "Start recording"}
          >
            <svg className="voice-ptt-icon" width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
