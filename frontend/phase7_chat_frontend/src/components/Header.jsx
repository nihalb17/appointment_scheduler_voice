import "./Header.css";

export default function Header({ mode = "chat", onModeChange, voiceDisabled = false, onBack }) {
  return (
    <div className="header">
      <div className="header-left">
        <button className="back-btn" onClick={onBack} title="Go Back">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        <div className="avatar">L</div>
        <div className="header-info">
          <span className="header-title">LakshmiAI</span>
          <span className="header-status">
            <span className="status-dot" />
            Active
          </span>
        </div>
      </div>
      <div className="header-tabs">
        <button
          type="button"
          className={`tab ${mode === "chat" ? "tab-active" : "tab-inactive-clickable"}`}
          onClick={() => onModeChange?.("chat")}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          Chat
        </button>
        <button
          type="button"
          className={`tab ${mode === "voice" ? "tab-active" : voiceDisabled ? "tab-inactive" : "tab-inactive-clickable"}`}
          onClick={() => !voiceDisabled && onModeChange?.("voice")}
          disabled={voiceDisabled}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M4 10v4M7 8v8M10 6v12M13 9v6M16 7v10M19 11v2" />
          </svg>
          Voice
        </button>
      </div>
    </div>
  );
}
