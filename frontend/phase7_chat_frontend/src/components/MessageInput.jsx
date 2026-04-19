import { useState, useRef, useEffect } from "react";
import "./MessageInput.css";

export default function MessageInput({ onSend, disabled }) {
  const [text, setText] = useState("");
  const inputRef = useRef(null);

  // Auto-focus input when it becomes enabled (after agent replies)
  useEffect(() => {
    if (!disabled && inputRef.current) {
      inputRef.current.focus();
    }
  }, [disabled]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
  };

  return (
    <form className="input-bar" onSubmit={handleSubmit}>
      <input
        ref={inputRef}
        className="input-field"
        type="text"
        placeholder="Message..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
      />
      <button className="send-btn" type="submit" disabled={!text.trim() || disabled}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="12" y1="19" x2="12" y2="5" />
          <polyline points="5 12 12 5 19 12" />
        </svg>
      </button>
    </form>
  );
}
