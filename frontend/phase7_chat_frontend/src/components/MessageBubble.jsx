import { useState, useEffect } from "react";
import "./MessageBubble.css";

export default function MessageBubble({ role, text, stream }) {
  const isBot = role === "assistant";
  const [displayedText, setDisplayedText] = useState(isBot && stream ? "" : text);

  useEffect(() => {
    if (!isBot || !stream) {
      setDisplayedText(text);
      return;
    }

    // Typewriter effect for bot messages
    const safeText = text || "";
    let currentIndex = 0;
    const words = safeText.split(" ");
    setDisplayedText(""); // Reset
    
    const interval = setInterval(() => {
      if (currentIndex < words.length) {
        const nextWord = words[currentIndex];
        if (nextWord !== undefined) {
          setDisplayedText((prev) => (prev ? prev + " " + nextWord : nextWord));
        }
        currentIndex++;
      } else {
        clearInterval(interval);
      }
    }, 70);

    return () => clearInterval(interval);
  }, [isBot, text]);

  return (
    <div className={`bubble-row ${isBot ? "bubble-left" : "bubble-right"}`}>
      <div className={`bubble ${isBot ? "bubble-bot" : "bubble-user"}`}>
        {displayedText}
      </div>
    </div>
  );
}
