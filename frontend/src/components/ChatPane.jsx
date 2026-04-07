import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../api/resumes";

export default function ChatPane({ chatHistory, resumeId, phase, dispatch }) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [lockedMsg, setLockedMsg] = useState(null);
  const bottomRef = useRef(null);

  const isLocked =
    phase === "FINALIZING" || phase === "DONE" || lockedMsg !== null;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  async function handleSend() {
    const message = input.trim();
    if (!message || sending || isLocked) return;

    setInput("");
    setSending(true);

    // Snapshot history BEFORE dispatch so backend receives history without current message
    const historyBeforeSend = [...chatHistory];
    dispatch({ type: "CHAT_SENT", message });

    try {
      const response = await sendChatMessage(
        resumeId,
        message,
        historyBeforeSend,
      );
      dispatch({
        type: "CHAT_RECEIVED",
        draft: response,
        reply: response.assistant_reply,
      });
    } catch (err) {
      if (err.message.toLowerCase().includes("finalized")) {
        setLockedMsg("Resume is finalized. No further changes.");
      } else {
        // CHAT_FAILED lets the reducer pop the optimistic message that CHAT_SENT appended
        dispatch({ type: "CHAT_FAILED", message: err.message });
      }
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-full min-h-[400px] bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {chatHistory.length === 0 && (
          <p className="text-gray-400 text-sm text-center pt-8">
            Clarifying questions will appear here after the draft is generated.
          </p>
        )}
        {chatHistory.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-blue-700 text-white"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {lockedMsg ? (
        <div className="border-t border-gray-200 px-4 py-3 text-sm text-gray-500 italic">
          {lockedMsg}
        </div>
      ) : isLocked ? (
        <div className="border-t border-gray-200 px-4 py-3 text-sm text-gray-400 italic">
          Chat locked — resume is being finalized.
        </div>
      ) : (
        <div className="border-t border-gray-200 px-4 py-3 flex gap-2">
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Reply or ask a follow-up..."
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg self-end transition-colors"
          >
            {sending ? "..." : "Send"}
          </button>
        </div>
      )}
    </div>
  );
}
