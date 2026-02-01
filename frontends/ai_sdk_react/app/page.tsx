"use client";

import { useChat } from "@ai-sdk/react";
import { useState } from "react";

export default function Chat() {
  const { messages, sendMessage, status } = useChat();
  const [input, setInput] = useState("");

  const isLoading = status === "submitted" || status === "streaming";

  return (
    <div
      style={{
        maxWidth: 700,
        margin: "0 auto",
        padding: "2rem",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <h1>Modal Jazz Chat</h1>

      <div style={{ marginBottom: "1rem" }}>
        {messages.map((m) => (
          <div key={m.id} style={{ marginBottom: "1rem" }}>
            <strong>{m.role === "user" ? "You" : "Assistant"}</strong>
            {m.parts.map((part, i) => {
              if (part.type === "reasoning") {
                return (
                  <details key={i} style={{ opacity: 0.6 }}>
                    <summary>Reasoning</summary>
                    <pre style={{ whiteSpace: "pre-wrap" }}>{part.text}</pre>
                  </details>
                );
              }
              if (part.type === "text") {
                return (
                  <p
                    key={i}
                    style={{ whiteSpace: "pre-wrap", margin: "0.25rem 0" }}
                  >
                    {part.text}
                  </p>
                );
              }
              return null;
            })}
          </div>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!input.trim()) return;
          sendMessage({ text: input });
          setInput("");
        }}
        style={{ display: "flex", gap: "0.5rem" }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Say something..."
          disabled={isLoading}
          style={{ flex: 1, padding: "0.5rem" }}
        />
        <button
          type="submit"
          disabled={isLoading}
          style={{ padding: "0.5rem 1rem" }}
        >
          Send
        </button>
      </form>
    </div>
  );
}
