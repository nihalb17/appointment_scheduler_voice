/** Default dev API port (see run_dev.ps1). Override with VITE_API_URL if needed. */
const DEFAULT_API_ORIGIN = "http://127.0.0.1:8020";

/** HTTP API: in dev, use relative URLs so Vite proxies to the backend. */
export const API_URL = import.meta.env.DEV
  ? ""
  : (import.meta.env.VITE_API_URL || DEFAULT_API_ORIGIN);

/** Voice WebSocket must hit the API port directly (same host as DEFAULT_API_ORIGIN / VITE_API_URL). */
const VOICE_HTTP_ORIGIN = (
  import.meta.env.VITE_API_URL || DEFAULT_API_ORIGIN
).replace(/\/$/, "");

let sessionId = crypto.randomUUID();

export function getSessionId() {
  return sessionId;
}

export function resetSession() {
  sessionId = crypto.randomUUID();
}

export function voiceWebSocketUrl() {
  const base = VOICE_HTTP_ORIGIN.startsWith("http")
    ? VOICE_HTTP_ORIGIN
    : `https://${VOICE_HTTP_ORIGIN}`;
  const u = new URL(base);
  const proto = u.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${u.host}/voice/ws?session_id=${encodeURIComponent(sessionId)}`;
}

export async function sendMessage(message) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}

// Phase 2: Eligibility Check APIs
export async function checkBookingEligibility(topic, timeSlot) {
  const res = await fetch(`${API_URL}/eligibility/book`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, topic, time_slot: timeSlot }),
  });

  if (!res.ok) {
    throw new Error(`Eligibility check error: ${res.status}`);
  }

  return res.json();
}

export async function checkCancellationEligibility(bookingCode) {
  const res = await fetch(`${API_URL}/eligibility/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, booking_code: bookingCode }),
  });

  if (!res.ok) {
    throw new Error(`Eligibility check error: ${res.status}`);
  }

  return res.json();
}

// Internal Dashboard APIs
export async function listKnowledgeBaseFiles() {
  const res = await fetch(`${API_URL}/internal/files`);
  
  if (!res.ok) {
    throw new Error(`Failed to list files: ${res.status}`);
  }
  
  return res.json();
}

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  
  const res = await fetch(`${API_URL}/internal/upload`, {
    method: "POST",
    body: formData,
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || `Upload failed: ${res.status}`);
  }
  
  return res.json();
}

export async function deleteFile(filename) {
  const res = await fetch(`${API_URL}/internal/files/${encodeURIComponent(filename)}`, {
    method: "DELETE",
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || `Delete failed: ${res.status}`);
  }
  
  return res.json();
}

export function getDownloadUrl(filename) {
  return `${API_URL}/internal/download/${encodeURIComponent(filename)}`;
}

// Phase 3: Approval APIs
export async function createApproval(action, details) {
  const res = await fetch(`${API_URL}/approval/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      action,
      ...details,
    }),
  });

  if (!res.ok) {
    throw new Error(`Approval creation error: ${res.status}`);
  }

  return res.json();
}

export async function confirmApproval(decision) {
  const res = await fetch(`${API_URL}/approval/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      decision,
    }),
  });

  if (!res.ok) {
    throw new Error(`Approval confirmation error: ${res.status}`);
  }

  return res.json();
}

export async function getPendingApproval() {
  const res = await fetch(`${API_URL}/approval/pending/${sessionId}`);

  if (!res.ok) {
    throw new Error(`Get pending approval error: ${res.status}`);
  }

  return res.json();
}

// Phase 4: Execution APIs
export async function executeBooking(topic, timeSlot, eligibilityDetails = null) {
  const res = await fetch(`${API_URL}/execution/book`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      topic,
      time_slot: timeSlot,
      eligibility_details: eligibilityDetails,
    }),
  });

  if (!res.ok) {
    throw new Error(`Booking execution error: ${res.status}`);
  }

  return res.json();
}

export async function executeCancellation(bookingCode, eligibilityDetails = null) {
  const res = await fetch(`${API_URL}/execution/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      booking_code: bookingCode,
      eligibility_details: eligibilityDetails,
    }),
  });

  if (!res.ok) {
    throw new Error(`Cancellation execution error: ${res.status}`);
  }

  return res.json();
}

// Phase 5: Confirmation API
export async function buildConfirmation(action, success, userMessage, bookingCode = null, eventLink = null, docLink = null, scheduledTime = null) {
  const res = await fetch(`${API_URL}/confirmation/build`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      action,
      success,
      user_message: userMessage,
      booking_code: bookingCode,
      event_link: eventLink,
      doc_link: docLink,
      scheduled_time: scheduledTime,
    }),
  });

  if (!res.ok) {
    throw new Error(`Confirmation build error: ${res.status}`);
  }

  return res.json();
}
