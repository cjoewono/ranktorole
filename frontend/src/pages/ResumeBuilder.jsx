import { useReducer, useEffect } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import NavBar from "../components/NavBar";
import UploadForm from "../components/UploadForm";
import SplitPane from "../components/SplitPane";
import DraftPane from "../components/DraftPane";
import ChatPane from "../components/ChatPane";
import { generateDraft, sendChatMessage, getResume } from "../api/resumes";

const initialState = {
  phase: "IDLE", // IDLE | LOADING | UPLOADED | DRAFTING | REVIEWING | FINALIZING | DONE
  resumeId: null,
  jobDescription: "",
  draft: null, // { civilian_title, summary, roles[] }
  aiInitialDraft: null, // frozen snapshot of roles[] from DRAFT_RECEIVED — never overwritten
  chatHistory: [], // display-only — [{ role, content }] — NOT sent to backend
  aiSuggestions: null, // roles[] from chat response when phase === FINALIZING
  error: null,
};

function reducer(state, action) {
  switch (action.type) {
    case "JD_CHANGED":
      return { ...state, jobDescription: action.value };
    case "UPLOADED":
      return { ...state, phase: "UPLOADED", resumeId: action.resumeId };
    case "DRAFT_STARTED":
      return { ...state, phase: "DRAFTING", error: null };
    case "DRAFT_RECEIVED":
      return {
        ...state,
        phase: "REVIEWING",
        draft: action.draft,
        aiInitialDraft: action.draft.roles, // frozen snapshot — never updated by chat
        chatHistory: action.initialMessages,
      };
    case "DRAFT_FAILED":
      return { ...state, phase: "UPLOADED", error: action.message };
    case "CHAT_SENT":
      return {
        ...state,
        chatHistory: [
          ...state.chatHistory,
          { role: "user", content: action.message },
        ],
      };
    case "CHAT_RECEIVED":
      return {
        ...state,
        chatHistory: [
          ...state.chatHistory,
          { role: "assistant", content: action.reply },
        ],
      };
    case "CHAT_UPDATED":
      return {
        ...state,
        draft: {
          ...state.draft,
          roles: action.roles,
          civilian_title: action.civilian_title,
          summary: action.summary,
        },
      };
    case "CHAT_FAILED":
      // Pop the optimistically-added user message and set error
      return {
        ...state,
        chatHistory: state.chatHistory.slice(0, -1),
        error: action.message,
      };
    case "AI_SUGGESTIONS_RECEIVED":
      return { ...state, aiSuggestions: action.roles };
    case "AI_SUGGESTIONS_CLEARED":
      return { ...state, aiSuggestions: null };
    case "FINALIZE_STARTED":
      return { ...state, phase: "FINALIZING" };
    case "RETURN_TO_CHAT":
      return { ...state, phase: "REVIEWING", aiSuggestions: null };
    case "DONE":
      return { ...state, phase: "DONE" };
    case "ERROR":
      return { ...state, error: action.message };
    case "LOADING":
      return { ...state, phase: "LOADING" };
    case "RESUME_LOADED":
      return {
        ...state,
        phase: action.phase,
        resumeId: action.resumeId,
        draft: action.draft,
        aiInitialDraft: action.aiInitialDraft,
        chatHistory: action.chatHistory,
        error: null,
      };
    default:
      return state;
  }
}

export default function ResumeBuilder() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Resume re-entry from Dashboard — runs once on mount
  useEffect(() => {
    const id = searchParams.get("id");
    const mode = searchParams.get("mode");
    if (!id) return; // fresh session

    dispatch({ type: "LOADING" });
    getResume(id)
      .then((resume) => {
        dispatch({
          type: "RESUME_LOADED",
          resumeId: resume.id || id,
          phase: mode === "edit" ? "FINALIZING" : "REVIEWING",
          draft: {
            civilian_title: resume.civilian_title,
            summary: resume.summary,
            roles: resume.roles || [],
          },
          aiInitialDraft: resume.ai_initial_draft || resume.roles || [],
          chatHistory: (resume.chat_history || []).slice(-10), // last 10 messages for display
        });
      })
      .catch(() => {
        navigate("/dashboard");
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleGenerateDraft() {
    if (state.jobDescription.trim().length < 10) {
      dispatch({
        type: "ERROR",
        message: "Please paste a job description before generating your draft.",
      });
      return;
    }
    dispatch({ type: "DRAFT_STARTED" });
    try {
      const response = await generateDraft(
        state.resumeId,
        state.jobDescription,
      );
      dispatch({
        type: "DRAFT_RECEIVED",
        draft: {
          civilian_title: response.civilian_title,
          summary: response.summary,
          roles: response.roles,
        },
        initialMessages: response.clarifying_question
          ? [{ role: "assistant", content: response.clarifying_question }]
          : [],
      });
    } catch (err) {
      dispatch({ type: "DRAFT_FAILED", message: err.message });
    }
  }

  async function handleChatSend(message) {
    dispatch({ type: "CHAT_SENT", message });
    try {
      const response = await sendChatMessage(state.resumeId, message);
      dispatch({
        type: "CHAT_RECEIVED",
        reply: response.assistant_reply,
      });
      if (state.phase === "FINALIZING") {
        // Don't overwrite the draft being edited — surface as AI suggestions
        dispatch({
          type: "AI_SUGGESTIONS_RECEIVED",
          roles: response.roles,
        });
      } else {
        // REVIEWING — update the live draft as before
        dispatch({
          type: "CHAT_UPDATED",
          roles: response.roles,
          civilian_title: response.civilian_title,
          summary: response.summary,
        });
      }
    } catch (err) {
      dispatch({ type: "CHAT_FAILED", message: err.message });
    }
  }

  const isSplitPhase =
    state.phase === "REVIEWING" || state.phase === "FINALIZING";

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />

      {isSplitPhase ? (
        // SplitPane renders OUTSIDE the constrained <main> container so it can
        // fill the full remaining viewport height with a sticky right pane.
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
            />
          }
        />
      ) : (
        <main className="max-w-5xl mx-auto px-4 py-8">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Resume Builder</h1>
            <Link
              to="/dashboard"
              className="text-sm text-blue-600 hover:underline"
            >
              ← Back to Dashboard
            </Link>
          </div>

          {state.phase === "IDLE" || state.phase === "UPLOADED" ? (
            <UploadForm
              state={state}
              dispatch={dispatch}
              onGenerateDraft={handleGenerateDraft}
            />
          ) : state.phase === "LOADING" ? (
            <div className="text-center py-24 text-gray-400 text-sm">
              Loading resume…
            </div>
          ) : state.phase === "DRAFTING" ? (
            <div className="text-center py-24 text-gray-400 text-sm">
              Generating draft… this may take a few seconds.
            </div>
          ) : state.phase === "DONE" ? (
            <div className="text-center py-24 space-y-4">
              <p className="text-xl font-semibold text-gray-800">
                Resume finalized!
              </p>
              <Link
                to="/dashboard"
                className="inline-block bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold px-6 py-2.5 rounded-lg transition-colors"
              >
                Back to Dashboard
              </Link>
            </div>
          ) : null}

          {state.error &&
            state.phase !== "IDLE" &&
            state.phase !== "UPLOADED" && (
              <div className="mt-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
                {state.error}
              </div>
            )}
        </main>
      )}
    </div>
  );
}
