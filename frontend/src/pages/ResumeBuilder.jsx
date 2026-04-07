import { useReducer } from "react";
import NavBar from "../components/NavBar";
import { Link } from "react-router-dom";
import UploadForm from "../components/UploadForm";
import SplitPane from "../components/SplitPane";
import DraftPane from "../components/DraftPane";
import ChatPane from "../components/ChatPane";
import { generateDraft } from "../api/resumes";

const initialState = {
  phase: "IDLE", // IDLE | UPLOADED | DRAFTING | REVIEWING | FINALIZING | DONE
  resumeId: null,
  jobDescription: "",
  draft: null, // { civilian_title, summary, bullets, clarifying_questions }
  chatHistory: [], // [{ role, content }] — never persisted
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
        draft: action.draft,
        chatHistory: [
          ...state.chatHistory,
          { role: "assistant", content: action.reply },
        ],
      };
    case "CHAT_FAILED":
      // Pop the optimistically-added user message and set error
      return {
        ...state,
        chatHistory: state.chatHistory.slice(0, -1),
        error: action.message,
      };
    case "FINALIZE_STARTED":
      return { ...state, phase: "FINALIZING" };
    case "DONE":
      return { ...state, phase: "DONE" };
    case "ERROR":
      return { ...state, error: action.message };
    default:
      return state;
  }
}

export default function ResumeBuilder() {
  const [state, dispatch] = useReducer(reducer, initialState);

  async function handleGenerateDraft() {
    dispatch({ type: "DRAFT_STARTED" });
    try {
      const draft = await generateDraft(state.resumeId, state.jobDescription);
      dispatch({
        type: "DRAFT_RECEIVED",
        draft,
        initialMessages: draft.clarifying_questions.map((q) => ({
          role: "assistant",
          content: q,
        })),
      });
    } catch (err) {
      dispatch({ type: "DRAFT_FAILED", message: err.message });
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
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
        ) : state.phase === "DRAFTING" ? (
          <div className="text-center py-24 text-gray-400 text-sm">
            Generating draft… this may take a few seconds.
          </div>
        ) : state.phase === "REVIEWING" || state.phase === "FINALIZING" ? (
          <SplitPane
            left={
              <DraftPane
                draft={state.draft}
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
              />
            }
          />
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
    </div>
  );
}
