import { useState } from "react";
import ChatWindow from "./components/ChatWindow";
import LandingPage from "./components/LandingPage";

export default function App() {
  const [view, setView] = useState("landing");

  return (
    <div style={{ width: "100%", height: "100vh" }}>
      <LandingPage onStartChat={() => setView("chat")} />
      
      {view === "chat" && (
        <ChatWindow onClose={() => setView("landing")} />
      )}
    </div>
  );
}
