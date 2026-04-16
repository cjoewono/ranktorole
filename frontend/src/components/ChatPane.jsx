import { useState, useRef, useEffect } from "react";
import UpgradeModal from "./UpgradeModal";

export default function ChatPane({
  chatHistory = [],
  resumeId,
  phase,
  dispatch,
  onSend,
  isSending = false,
  chatTurnCount = 0,
  userTier = "free",
}) {
  const [input, setInput] = useState("");
  const [lockedMsg, setLockedMsg] = useState(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (phase === "REVIEWING" || phase === "FINALIZING") setLockedMsg(null);
  }, [phase]);

  const isLocked =
    phase === "DONE" ||
    lockedMsg !== null ||
    (userTier !== "pro" && chatTurnCount >= 10);

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
      if (err.status === 403 && err.data?.code === "CHAT_LIMIT_REACHED") {
        setLockedMsg("You've reached the 10 message limit.");
        setShowUpgrade(true);
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
      {/* Turn counter — free tier only */}
      {userTier !== "pro" && (
        <div
          className={`px-4 py-2 flex items-center justify-between border-b border-outline-variant/20 ${
            chatTurnCount >= 10
              ? "bg-error-container"
              : chatTurnCount >= 8
                ? "bg-tertiary/10"
                : "bg-surface-container-highest"
          }`}
        >
          <span className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
            AI Refinements
          </span>
          <span
            className={`font-label text-xs font-semibold tabular-nums ${
              chatTurnCount >= 10
                ? "text-error"
                : chatTurnCount >= 8
                  ? "text-tertiary"
                  : "text-on-surface-variant"
            }`}
          >
            {chatTurnCount >= 10
              ? "10 / 10 — Upgrade for unlimited"
              : `${chatTurnCount} / 10`}
          </span>
        </div>
      )}
      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {chatHistory.length === 0 && !isSending && (
          <p className="text-on-surface-variant text-sm text-center pt-8">
            {phase === "FINALIZING"
              ? "Ask for suggestions or request changes to any bullet."
              : "Clarifying questions will appear here after the draft is generated."}
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
          {phase === "DONE"
            ? "MISSION COMPLETE — RESUME FINALIZED"
            : chatTurnCount >= 10
              ? "CHAT LIMIT REACHED — UPGRADE FOR UNLIMITED"
              : "CHAT LOCKED — RESUME ALREADY FINALIZED"}
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

      <UpgradeModal
        open={showUpgrade}
        onClose={() => setShowUpgrade(false)}
        title="Chat limit reached"
        description="Free accounts get 10 refinement messages per resume. Upgrade to Pro for unlimited chat on every resume — $10/month."
      />
    </div>
  );
}
