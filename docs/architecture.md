# Multi-Agent Appointment Scheduler — Phase-wise Architecture

## Overview

A voice/chat appointment scheduler for a Mutual Fund (MF) Distributor. The system uses a multi-agent architecture to handle **booking** and **cancellation** of appointments, with all Google Workspace operations driven via **MCP tools**.

---

## Agents & LLMs

| Agent | LLM | Role |
|---|---|---|
| Orchestrator Agent | Groq | Routes user intent, manages conversation flow, asks for user approval before any calendar mutation |
| Eligibility Agent | Gemini | Validates whether a booking/cancellation request is eligible (slot availability, booking code verification) |
| Booking Agent | Gemini | Executes the full booking workflow (calendar event, Google Doc, email, sheet log) |
| Cancellation Agent | Gemini | Executes the full cancellation workflow (remove event, email, sheet log) |

## MCP Tools

| MCP Tool | Used By | Purpose |
|---|---|---|
| Calendar Read | Eligibility Agent | Read calendar to check slot availability / verify booking code |
| Calendar Write | Booking Agent, Cancellation Agent | Create or delete calendar events |
| Google Docs | Booking Agent | Create a Google Doc titled with topic + booking code and attach to calendar event |
| Gmail | Booking Agent, Cancellation Agent | Send email notification to MF distributor |
| Google Sheets | Booking Agent, Cancellation Agent | Log every action to a common sheet |

---

## Phase 1 — Intent Detection & Routing

**Actor:** User → Orchestrator Agent (Groq)

1. Orchestrator Agent receives the user's message (text, from either voice or chat).
2. Orchestrator classifies the intent into one of:
   - **Book** — route to Booking lane.
   - **Cancel** — route to Cancellation lane.
   - **Out-of-scope** — any question or request that is not related to booking or cancelling an appointment (e.g., investment advice, general queries, personal questions). The Orchestrator **does not** delegate to any sub-agent; it directly replies that it can only assist with appointment-related actions and politely declines.
3. For recognised intents, Orchestrator collects required inputs from the user:
   - **Booking:** appointment topic + desired time slot.
   - **Cancellation:** booking code.

**Appointment topics (enum):** KYC/Onboarding · SIP/Mandates · Statements/Tax Docs · Withdrawals & Timelines · Account Changes/Nominee

**Guardrails enforced at this phase:**
- Any question outside of booking/cancellation must be deflected — the agent responds that it is only here to help with appointments.
- The agent must never give investment advice.
- The agent must never collect personal information from the user.
- Reschedule is not supported — the agent must instruct the user to cancel first, then book a new appointment.

---

## Phase 2 — Eligibility Check

**Actor:** Eligibility Agent (Gemini) + Calendar Read MCP

### Booking Lane

1. Read the MF distributor's calendar via **Calendar Read MCP**.
2. Refer to the uploaded **knowledge base** for slot limits/rules.
3. Determine if the requested slot is available.
4. Decision:
   - **Eligible** → proceed to Phase 3.
   - **Not eligible** → inform user via Orchestrator (slot unavailable / limit reached).

### Cancellation Lane

1. Look up the booking code against the MF distributor's calendar via **Calendar Read MCP**.
2. Verify the calendar entry exists.
3. Decision:
   - **Eligible** → proceed to Phase 3.
   - **Not eligible** → inform user via Orchestrator (invalid booking code / event not found).

---

## Phase 3 — User Approval

**Actor:** Orchestrator Agent → User

1. Orchestrator presents a summary of the proposed action to the user:
   - **Booking:** topic, time slot, distributor calendar.
   - **Cancellation:** booking code, event details to be removed.
2. User confirms or rejects.
3. Decision:
   - **Approved** → proceed to Phase 4.
   - **Rejected** → end flow or let user modify inputs.

---

## Phase 4 — Execution

### Booking Lane

**Actor:** Booking Agent (Gemini) + MCP tools

Executes the following steps in order:

1. **Add event to calendar** — Calendar Write MCP. Generate a booking code.
2. **Create Google Doc** — Google Docs MCP. Title: `{Topic} — {Booking Code}`.
3. **Attach Google Doc to calendar event** — Calendar Write MCP (update event with doc link).
4. **Email MF distributor** — Gmail MCP. Include the Google Doc link.
5. **Log action to Google Sheets** — Sheets Write MCP. Append booking details to the common log sheet.

### Cancellation Lane

**Actor:** Cancellation Agent (Gemini) + MCP tools

Executes the following steps in order:

1. **Remove event from calendar** — Calendar Write MCP.
2. **Email MF distributor** — Gmail MCP. Notify about cancellation.
3. **Log action to Google Sheets** — Sheets Write MCP. Append cancellation details to the common log sheet.

---

## Phase 5 — Confirmation

**Actor:** Orchestrator Agent → User

1. Orchestrator receives the result from the Booking or Cancellation agent.
2. Sends a confirmation message to the user summarising what was done (booking code, event link, etc.).

---

## Phase 6 — Voice Agent

**Actor:** User ↔ Voice Layer

This phase covers the voice interface that wraps the agent pipeline. Both input and output use **streaming** to enable a natural, real-time conversational experience — similar to a phone call between two people, with no perceivable wait between speaking and hearing a response.

1. User speaks → audio is **streamed** in real time to the STT engine → transcribed text is forwarded to the Orchestrator Agent (Phase 1).
2. Orchestrator's text response is **streamed token-by-token** to the TTS engine → TTS begins generating audio as tokens arrive → audio chunks are **streamed back** and played to the user progressively (no need to wait for the full response).
3. Responsibilities:
   - Real-time audio streaming from user microphone to STT.
   - Streaming Orchestrator response tokens to TTS for incremental audio generation.
   - Progressive audio playback so the agent starts "speaking" while still generating.
   - Relaying confirmation prompts for the approval gate (Phase 3) via voice.

---

## Phase 7 — Chat Frontend

**Actor:** User ↔ Chat UI

This phase covers the chat-based frontend that provides a text interface to the agent pipeline.

1. User types a message → text is sent directly to the Orchestrator Agent (Phase 1).
2. Orchestrator's response is rendered as text in the chat UI.
3. Responsibilities:
   - Rendering agent text responses and conversation history.
   - Displaying confirmation prompts for the approval gate (Phase 3).
   - Providing the knowledge-base upload interface for the MF distributor.

---

## Flow Diagram

Refer to [`multi_agent_scheduler_parallel_v4 (1).svg`](./multi_agent_scheduler_parallel_v4%20(1).svg) for the full two-lane parallel flowchart.

---

## Cross-cutting Concerns

- **Knowledge Base Management:** A separate internal dashboard is available at the `/internal` endpoint. The MF distributor can use it to view, upload, download, and remove knowledge base files. These files are referenced by the Eligibility Agent to determine slot availability and limits.
- **Common Log Sheet:** Every booking and cancellation action is logged to a single shared Google Sheet.
- **No Reschedule Flow:** The system does not support rescheduling. Users must cancel the existing booking and then create a new one.
- **Approval Gate:** No calendar event is ever created or deleted without explicit user approval (Phase 3).
