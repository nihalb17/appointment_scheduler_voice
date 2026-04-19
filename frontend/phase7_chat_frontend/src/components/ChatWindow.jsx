import { useState, useRef, useEffect } from "react";
import Header from "./Header";
import MessageBubble from "./MessageBubble";
import QuickActions from "./QuickActions";
import MessageInput from "./MessageInput";
import VoicePanel from "./VoicePanel";
import { sendMessage, createApproval, confirmApproval, executeBooking, executeCancellation, buildConfirmation, resetSession } from "../services/api";
import "./ChatWindow.css";

const WELCOME_MSG =
  "Hi there! 👋 I'm LakshmiAI, your intelligent companion. I can help you book or cancel appointments with ease. What would you like to do today?";

export default function ChatWindow({ onClose }) {
  const [uiMode, setUiMode] = useState("chat");
  const [messages, setMessages] = useState([
    { role: "assistant", text: WELCOME_MSG },
  ]);
  const [showQuickActions, setShowQuickActions] = useState(true);
  const [loading, setLoading] = useState(false);
  const [pendingApproval, setPendingApproval] = useState(null);
  const [chatClosed, setChatClosed] = useState(false);
  const [confirmationBanner, setConfirmationBanner] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text) => {
    setShowQuickActions(false);
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      // Check if we have a pending approval and user is confirming
      const isConfirmation = /^(yes|yeah|sure|ok|okay|confirm|proceed|go ahead)/i.test(text.trim());
      
      if (pendingApproval && isConfirmation) {
        // User confirmed - execute the action
        await handleExecution(pendingApproval);
        setPendingApproval(null);
        setLoading(false);
        return;
      }
      
      if (pendingApproval && /^(no|nope|cancel|reject|don't|dont)/i.test(text.trim())) {
        // User rejected
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Okay, I've cancelled that request. Is there anything else I can help you with?" },
        ]);
        setPendingApproval(null);
        setLoading(false);
        return;
      }

      const data = await sendMessage(text);
      
      // Check if this is a confirmation prompt from the orchestrator
      const isConfirmationPrompt = /shall i proceed/i.test(data.reply);
      
      // Check if this is a confirmed booking ready for execution
      if (data.intent === "book_confirmed" && data.topic && data.time_slot) {
        // Execute the booking immediately
        await handleExecution({
          type: "book",
          topic: data.topic,
          time_slot: data.time_slot,
        });
        setLoading(false);
        return;
      }
      
      // Check if this is a confirmed cancellation ready for execution
      if (data.intent === "cancel_confirmed" && data.booking_code) {
        await handleExecution({
          type: "cancel",
          booking_code: data.booking_code,
        });
        setLoading(false);
        return;
      }
      
      if (isConfirmationPrompt && data.intent === "book" && data.topic && data.time_slot) {
        // Store pending booking for execution
        setPendingApproval({
          type: "book",
          topic: data.topic,
          time_slot: data.time_slot,
        });
      } else if (isConfirmationPrompt && data.intent === "cancel" && data.booking_code) {
        // Store pending cancellation for execution
        setPendingApproval({
          type: "cancel",
          booking_code: data.booking_code,
        });
      }
      
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: data.reply },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Sorry, something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleExecution = async (approval) => {
    try {
      if (approval.type === "book") {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Processing your booking..." },
        ]);
        
        const result = await executeBooking(approval.topic, approval.time_slot);
        
        if (result.success) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", text: result.user_message },
          ]);
          // Phase 5: Build confirmation
          try {
            const confirmation = await buildConfirmation(
              "book",
              true,
              result.user_message,
              result.result?.booking_code || null,
              result.result?.calendar_event?.event_link || null,
              result.result?.google_doc?.doc_link || null,
              result.result?.calendar_event?.start_time || null,
            );
            if (confirmation.close_chat) {
              setConfirmationBanner(confirmation.banner_text);
              setChatClosed(true);
            }
          } catch (e) {
            // Fallback: close chat even if confirmation API fails
            setConfirmationBanner("Appointment confirmed");
            setChatClosed(true);
          }
        } else {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", text: `Booking failed: ${result.message}` },
          ]);
        }
      } else if (approval.type === "cancel") {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Processing your cancellation..." },
        ]);
        
        const result = await executeCancellation(approval.booking_code);
        
        if (result.success) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", text: result.user_message },
          ]);
          // Phase 5: Build confirmation
          try {
            const confirmation = await buildConfirmation(
              "cancel",
              true,
              result.user_message,
              result.result?.booking_code || null,
            );
            if (confirmation.close_chat) {
              setConfirmationBanner(confirmation.banner_text);
              setChatClosed(true);
            }
          } catch (e) {
            // Fallback: close chat even if confirmation API fails
            setConfirmationBanner("Appointment cancelled");
            setChatClosed(true);
          }
        } else {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", text: `Cancellation failed: ${result.message}` },
          ]);
        }
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `Error: ${error.message}` },
      ]);
    }
  };

  return (
    <div className="chat-overlay">
      <div className="chat-window">
        <Header mode={uiMode} onModeChange={setUiMode} onBack={onClose} />

        <div className="messages-area">
          {messages.map((msg, i) => (
            <MessageBubble key={i} role={msg.role} text={msg.text} stream={msg.stream} />
          ))}

          {uiMode === "chat" && showQuickActions && <QuickActions onAction={handleSend} />}

          {uiMode === "chat" && loading && (
            <div className="typing-indicator">
              <span /><span /><span />
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {uiMode === "chat" && !chatClosed && (
          <MessageInput onSend={handleSend} disabled={loading || chatClosed} />
        )}

        {uiMode === "voice" && (
          <VoicePanel
            disabled={chatClosed}
            onUserTranscript={(text) =>
              setMessages((prev) => [...prev, { role: "user", text }])
            }
            onAssistantMessage={(text, stream) =>
              setMessages((prev) => [...prev, { role: "assistant", text, stream }])
            }
            onVoiceCallComplete={(payload) => {
              setConfirmationBanner(payload.banner_text || "Appointment confirmed");
              setChatClosed(true);
            }}
          />
        )}

        {confirmationBanner && (
          <div className="confirmation-banner">
            <svg className="confirmation-tick" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="9 12 11.5 14.5 16 10" />
            </svg>
            <span>{confirmationBanner}</span>
          </div>
        )}
      </div>
    </div>
  );
}
