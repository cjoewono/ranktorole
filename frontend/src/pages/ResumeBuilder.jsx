import { useEffect } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import UploadForm from "../components/UploadForm";
import SplitPane from "../components/SplitPane";
import DraftPane from "../components/DraftPane";
import ChatPane from "../components/ChatPane";
import useResumeMachine from "../hooks/useResumeMachine";
import { useAuth } from "../context/AuthContext";

export default function ResumeBuilder({ setFullscreen }) {
  const { state, dispatch, handleGenerateDraft, handleChatSend } =
    useResumeMachine();
  const { user } = useAuth();

  const isSplitPhase =
    state.phase === "REVIEWING" ||
    state.phase === "FINALIZING" ||
    state.phase === "DONE";

  useEffect(() => {
    setFullscreen(isSplitPhase);
  }, [isSplitPhase, setFullscreen]);

  if (isSplitPhase) {
    return (
      <SplitPane
        left={
          <DraftPane
            draft={state.draft}
            aiInitialDraft={state.aiInitialDraft}
            aiSuggestions={state.aiSuggestions}
            phase={state.phase}
            dispatch={dispatch}
            resumeId={state.resumeId}
          />
        }
        right={
          <ChatPane
            chatHistory={state.chatHistory}
            resumeId={state.resumeId}
            phase={state.phase}
            dispatch={dispatch}
            onSend={handleChatSend}
            isSending={state.isSending}
            chatTurnCount={state.chatTurnCount}
            userTier={user?.tier || "free"}
          />
        }
      />
    );
  }

  return (
    <div className="pb-20 md:pb-0">
      <PageHeader
        label="RESUME BUILDER / INITIALIZE"
        title="NEW DEPLOYMENT"
        action={
          <Link
            to="/dashboard"
            className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
          >
            ← DASHBOARD
          </Link>
        }
      />
      <main className="max-w-2xl mx-auto px-4 py-8">
        {(state.phase === "IDLE" || state.phase === "UPLOADED") && (
          <UploadForm
            state={state}
            dispatch={dispatch}
            onGenerateDraft={handleGenerateDraft}
          />
        )}
        {state.phase === "LOADING" && (
          <div className="text-center py-24 font-label text-xs tracking-widest uppercase text-on-surface-variant">
            LOADING DEPLOYMENT...
          </div>
        )}
        {state.phase === "DRAFTING" && (
          <div className="text-center py-24 space-y-3">
            <div className="flex justify-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
              <span className="w-2 h-2 rounded-full bg-secondary animate-pulse [animation-delay:150ms]" />
              <span className="w-2 h-2 rounded-full bg-secondary animate-pulse [animation-delay:300ms]" />
            </div>
            <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
              GENERATING TACTICAL BRIEF...
            </p>
          </div>
        )}
        {state.error &&
          state.phase !== "IDLE" &&
          state.phase !== "UPLOADED" && (
            <div className="mt-4 bg-error-container text-on-error-container font-body text-sm px-4 py-3">
              {state.error}
            </div>
          )}
      </main>
    </div>
  );
}
