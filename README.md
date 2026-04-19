# Multi-Agent Voice & Chat Appointment Scheduler
**Automated Booking & Cancellation for MF Distributors**

[![Live App](https://img.shields.io/badge/Live-Vercel-black?logo=vercel)](https://appointment-scheduler-voice.vercel.app/)

An AI-driven appointment scheduling system featuring a multi-agent architecture that handles complex scheduling logic through natural voice and chat interfaces.

## 🧠 Multi-Agent Parallel Architecture

The system uses a two-lane parallel structure to ensure distinct logic for booking and cancellation paths, orchestrated by a central intent-routing agent.

```mermaid
graph TD
    %% Global Styles
    classDef orch fill:#EEEDFE,stroke:#534AB7,stroke-width:1px,color:#3C3489
    classDef elig fill:#E1F5EE,stroke:#0F6E56,stroke-width:1px,color:#085041
    classDef book fill:#F5C4B3,stroke:#993C1D,stroke-width:1px,color:#712B13
    classDef cancel fill:#FB3A0,stroke:#993556,stroke-width:1px,color:#72243E
    classDef user fill:#F1EFE8,stroke:#5F5E5A,stroke-width:1px,color:#444441
    classDef decision fill:#F5F4ED,stroke:#1F1E1D,stroke-width:0.3px,color:#141413
    classDef mcp fill:#E6F1FB,stroke:#185FA5,stroke-width:1px,color:#185FA5
    classDef fail fill:#FCEBEB,stroke:#A32D2D,stroke-width:1px,color:#A32D2D

    %% Shared Top
    U([👤 User<br/>Voice / Chat]):::user
    O1{🧠 Orchestrator Agent<br/>Groq}:::orch
    Intent{Intent}:::decision

    U --> O1
    O1 --> Intent

    subgraph "Booking Lane"
        B_Elig[Eligibility Agent<br/>Gemini]:::elig
        B_MCP[Calendar Read]:::mcp
        B_IsElig{Eligible}:::decision
        B_Fail([No]):::fail
        B_Approve[Orchestrator Agent<br/>Approval Gate]:::orch
        B_Exec[Booking Agent<br/>Gemini]:::book
        B_Steps[1. Add Calendar Event<br/>2. Create Google Doc<br/>3. Attach Doc to Event<br/>4. Email Distributor<br/>5. Log to Sheets]:::book
    end

    subgraph "Cancellation Lane"
        C_Elig[Eligibility Agent<br/>Gemini]:::elig
        C_MCP[Calendar Read]:::mcp
        C_IsElig{Eligible}:::decision
        C_Fail([No]):::fail
        C_Approve[Orchestrator Agent<br/>Approval Gate]:::orch
        C_Exec[Cancellation Agent<br/>Gemini]:::cancel
        C_Steps[1. Remove Event<br/>2. Email Distributor<br/>3. Log to Sheets]:::cancel
    end

    %% Routing
    Intent -->|Book| B_Elig
    Intent -->|Cancel| C_Elig

    %% Booking Flow
    B_Elig --- B_MCP
    B_Elig --> B_IsElig
    B_IsElig -->|No| B_Fail
    B_IsElig -->|Yes| B_Approve
    B_Approve -->|Approved| B_Exec
    B_Exec --> B_Steps
    B_Steps --- B_CalW[Cal Write]:::mcp
    B_Steps --- B_SheetW[Sheets Write]:::mcp

    %% Cancellation Flow
    C_Elig --- C_MCP
    C_Elig --> C_IsElig
    C_IsElig -->|No| C_Fail
    C_IsElig -->|Yes| C_Approve
    C_Approve -->|Approved| C_Exec
    C_Exec --> C_Steps
    C_Steps --- C_CalW[Cal Write]:::mcp
    C_Steps --- C_SheetW[Sheets Write]:::mcp

    %% Converge
    B_Steps --> O2{Orchestrator Agent}:::orch
    C_Steps --> O2
    O2 --> Confirm([✅ Confirmation to User]):::user

    style "Booking Lane" fill:none,stroke:#993C1D,stroke-dasharray: 5 5
    style "Cancellation Lane" fill:none,stroke:#993556,stroke-dasharray: 5 5
```

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| **Backend** | FastAPI (Python) |
| **Frontend** | React + Vite (JS) |
| **LLMs** | Groq (Llama-3), Gemini-2.5-flash |
| **Voice** | Sarvam AI (Streaming STT/TTS) |
| **Database** | ChromaDB (Vector Store for RAG) |
| **Deployment** | Render (Backend), Vercel (Frontend) |

## 🔧 Setup & Deployment

1. **Backend (Render)**: Deploy using the root-level `Dockerfile`.
2. **Frontend (Vercel)**: Import repo, set root to `frontend/phase7_chat_frontend`.
3. **Live URL**: [https://appointment-scheduler-voice.vercel.app/](https://appointment-scheduler-voice.vercel.app/)

## 📁 Project Structure

- `backend/`: FastAPI application split into 7 specialized phases.
- `frontend/`: Modern chat and voice interface.
- `knowledge_base/`: Repository for holidays and eligibility rules.
- `docs/`: Detailed architecture and phase-wise documentation.
