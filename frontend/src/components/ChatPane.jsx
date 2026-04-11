import { useState, useRef, useEffect } from "react";

export default function ChatPane({
  chatHistory = [],
  resumeId,
  phase,
  dispatch,
  onSend,
  isSending = false,
}) {
  const [input, setInput] = useState("");
  const [lockedMsg, setLockedMsg] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (phase === "REVIEWING" || phase === "FINALIZING") setLockedMsg(null);
  }, [phase]);

  const isLocked = phase === "DONE" || lockedMsg !== null;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, isSending]);

  async function handleSend() {
    const message = input.trim();
    if (!message || isSending || isLocked) return;
    setInput("");
    try {
      await onSend(message);
    } catch (err) {
      if (err.status === 409) {
        setLockedMsg("Resume is finalized. No further changes.");
      }
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-full bg-surface-container">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {chatHistory.length === 0 && !isSending && (
          <p className="text-on-surface-variant text-sm text-center pt-8">
            Clarifying questions will appear here after the draft is generated.
          </p>
        )}
        {phase === "FINALIZING" && (
          <p className="text-xs text-tertiary bg-surface-container-highest rounded-md px-3 py-2 text-center">
            You can still chat to get AI suggestions while editing.
          </p>
        )}
        {(chatHistory || []).map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "mission-gradient text-on-primary rounded-2xl rounded-br-sm"
                  : "bg-surface-container-high text-on-surface rounded-2xl rounded-bl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Thinking bubble — visible while isSending */}
        {isSending && (
          <div className="flex justify-start">
            <div className="bg-surface-container-high text-on-surface rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse" />
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse [animation-delay:300ms]" />
              <span className="font-label text-xs tracking-widest uppercase text-on-surface-variant ml-1">
                PROCESSING REQUEST...
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      {lockedMsg ? (
        <div className="border-t border-outline-variant/20 px-4 py-3 text-sm text-on-surface-variant italic">
          {lockedMsg}
        </div>
      ) : isLocked ? (
        <div className="border-t border-outline-variant/20 px-4 py-3 font-label text-xs tracking-widest uppercase text-on-surface-variant">
          MISSION COMPLETE — RESUME FINALIZED
        </div>
      ) : (
        <div className="border-t border-outline-variant/20 px-4 py-3 flex gap-2">
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSending}
            placeholder={
              phase === "FINALIZING"
                ? "Ask for suggestions while editing…"
                : "Reply or ask a follow-up..."
            }
            className="tactical-input flex-1 resize-none disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isSending}
            className="mission-gradient disabled:opacity-50 text-on-primary font-label font-semibold tracking-widest uppercase text-sm px-4 py-2 rounded-md self-end transition-colors"
          >
            {isSending ? "SENDING..." : "SEND"}
          </button>
        </div>
      )}
    </div>
  );
}
