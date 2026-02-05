"use client";

import { useChat } from "@ai-sdk/react";
import { useEffect, useRef, useState } from "react";
import type { UIMessage } from "ai";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

const SUGGESTIONS = [
  "Explain how transformers work.",
  "Write five different programs for me in both Python and Rust.",
  "What is Modal and how does it work?",
];

const markdownComponents: Components = {
  code({ className, children, ...props }) {
    const isBlock = className?.startsWith("hljs");
    if (isBlock) {
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code
        className="bg-green-dim text-green-bright px-1.5 py-0.5 rounded text-xs font-mono"
        {...props}
      >
        {children}
      </code>
    );
  },
  a({ children, ...props }) {
    return (
      <a target="_blank" rel="noopener noreferrer" {...props}>
        {children}
      </a>
    );
  },
};

function MarkdownContent({ children }: { children: string }) {
  return (
    <div className="prose prose-xs sm:prose-sm prose-invert max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={markdownComponents}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}

function EmptyState({ onSend }: { onSend: (text: string) => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 gap-6">
      <h2 className="text-3xl sm:text-4xl font-light text-green-bright py-4">Modal Jazz</h2>
      <p className="text-text-primary/50 text-sm">Ask me anything.</p>
      <div className="flex flex-wrap justify-center gap-2 max-w-lg">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSend(s)}
            className="rounded-full border border-border px-4 py-2 text-sm text-text-primary/70 hover:border-green-bright/40 hover:text-green-bright hover:bg-green-dim transition-all cursor-pointer"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-bg-container rounded-2xl px-5 py-4 max-w-[85%]">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="block w-2 h-2 rounded-full bg-green-bright"
              style={{
                animation: "pulse-dot 1.4s ease-in-out infinite",
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  isStreaming,
}: {
  message: UIMessage;
  isStreaming: boolean;
}) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[95%] sm:max-w-[85%] rounded-2xl px-4 py-3 sm:px-5 sm:py-4 ${
          isUser ? "bg-green-dim" : "bg-bg-container"
        }`}
      >
        {!isUser && (
          <span className="block text-xs text-green-bright/70 font-medium mb-2">
            Assistant
          </span>
        )}

        {message.parts.map((part, i) => {
          if (part.type === "tool-webSearch") {
            return (
              <details
                key={i}
                className="my-2 border border-border rounded-xl overflow-hidden"
              >
                <summary className="px-3 py-2 text-xs text-green-bright/70 font-medium cursor-pointer hover:bg-green-dim transition-colors">
                  Web Search
                  {part.state === "input-available" && " (searching...)"}
                </summary>
                <div className="px-3 py-2 text-xs text-text-primary/80 border-t border-border">
                  {part.state === "input-available" && (
                    <div className="italic text-text-primary/50">
                      Searching for: {(part.input as any)?.query}
                    </div>
                  )}
                  {part.state === "output-available" && (
                    <div className="space-y-2">
                      {(part.output as any)?.results?.map((result: any, idx: number) => (
                        <div
                          key={idx}
                          className="border-l-2 border-green-dim pl-2"
                        >
                          <a
                            href={result.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-green-bright hover:underline font-medium block"
                          >
                            {result.title}
                          </a>
                          <div className="text-text-primary/60 text-xs mt-1 line-clamp-3">
                            {result.content}
                          </div>
                        </div>
                      ))}
                      {!(part.output as any)?.results?.length && (
                        <div className="text-text-primary/50 italic">
                          No results found
                        </div>
                      )}
                    </div>
                  )}
                  {part.state === "output-error" && (
                    <div className="text-red-400/80 italic">
                      Error: {(part as any).errorText}
                    </div>
                  )}
                </div>
              </details>
            );
          }
          if (part.type === "reasoning") {
            return (
              <details
                key={i}
                className="my-2 border border-border rounded-xl overflow-hidden"
              >
                <summary className="px-3 py-2 text-xs text-text-primary/50 font-mono cursor-pointer hover:bg-green-dim transition-colors">
                  Reasoning
                </summary>
                <div className="px-3 py-2 text-xs text-text-primary/60 font-mono border-t border-border">
                  <MarkdownContent>{part.text}</MarkdownContent>
                </div>
              </details>
            );
          }
          if (part.type === "text") {
            if (isUser) {
              return (
                <p
                  key={i}
                  className="whitespace-pre-wrap text-xs sm:text-sm leading-relaxed"
                >
                  {part.text}
                </p>
              );
            }
            return (
              <div key={i} className="text-xs sm:text-sm leading-relaxed">
                <MarkdownContent>{part.text}</MarkdownContent>
                {isStreaming && i === message.parts.length - 1 && (
                  <span className="inline-block w-2 h-4 ml-0.5 bg-green-bright/80 rounded-sm animate-pulse align-middle" />
                )}
              </div>
            );
          }
          return null;
        })}
      </div>
    </div>
  );
}

export default function Chat() {
  const { messages, sendMessage, status } = useChat();
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const isLoading = status === "submitted" || status === "streaming";

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [input]);

  // Auto-scroll on new messages
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, status]);

  function handleSend(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;
    sendMessage({ text: trimmed });
    setInput("");
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {!hasMessages ? (
          <EmptyState onSend={handleSend} />
        ) : (
          <div className="max-w-3xl mx-auto w-full px-4 py-6 flex flex-col gap-4">
            {messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                isStreaming={
                  status === "streaming" &&
                  m === messages[messages.length - 1] &&
                  m.role === "assistant"
                }
              />
            ))}
            {status === "submitted" && <ThinkingIndicator />}
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-border">
        <div className="w-full px-4 py-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend(input);
            }}
            className="flex gap-3 items-end max-w-3xl mx-auto"
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(input);
                }
              }}
              placeholder="Send a message..."
              disabled={isLoading}
              rows={1}
              className="flex-1 bg-bg-container border border-border rounded-xl px-4 py-3 text-sm text-text-primary placeholder:text-text-primary/30 focus:outline-none focus:border-green-bright/50 resize-none disabled:opacity-40 transition-colors"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-green-bright text-bg-base font-medium rounded-xl px-5 py-3 text-sm hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer shrink-0"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
