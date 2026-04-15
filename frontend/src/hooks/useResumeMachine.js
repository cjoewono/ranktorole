import { useReducer, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
  generateDraft,
  sendChatMessage,
  getResume,
  reopenResume,
} from "../api/resumes";
import { useResumes } from "../context/ResumeContext";

const initialState = {
  phase: "IDLE", // IDLE | LOADING | UPLOADED | DRAFTING | REVIEWING | FINALIZING | DONE
  resumeId: null,
  jobDescription: "",
  draft: null, // { civilian_title, summary, roles[] }
  aiInitialDraft: null, // frozen snapshot of roles[] from DRAFT_RECEIVED — never overwritten
  chatHistory: [], // display-only — [{ role, content }] — NOT sent to backend
  aiSuggestions: null, // roles[] from chat response when phase === FINALIZING
  isSending: false,
  isFinalized: false,
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
      return {
        ...state,
        phase: "DONE",
        isFinalized: true,
        ...(action.draft ? { draft: action.draft } : {}),
      };
    case "ERROR":
      return { ...state, error: action.message };
    case "LOADING":
      return { ...state, phase: "LOADING" };
    case "RESET":
      return { ...initialState };
    case "RESUME_LOADED":
      return {
        ...state,
        phase: action.phase,
        resumeId: action.resumeId,
        draft: action.draft,
        aiInitialDraft: action.aiInitialDraft,
        chatHistory: action.chatHistory,
        isFinalized: action.isFinalized || false,
        error: null,
      };
    case "CHAT_SENDING":
      return { ...state, isSending: true };
    case "CHAT_DONE_SENDING":
      return { ...state, isSending: false };
    default:
      return state;
  }
}

export default function useResumeMachine() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [searchParams] = useSearchParams();
  const { refreshResumes } = useResumes();
  const navigate = useNavigate();
  const loadedIdRef = useRef(null);

  const id = searchParams.get("id");
  const mode = searchParams.get("mode");

  // Resume re-entry from Dashboard — re-runs whenever ?id param changes
  useEffect(() => {
    if (!id) {
      // Navigated to /resume-builder without params — reset to fresh state
      if (loadedIdRef.current !== null) {
        loadedIdRef.current = null;
        dispatch({ type: "RESET" });
      }
      return;
    }
    if (loadedIdRef.current === id) return; // already loaded this resume

    loadedIdRef.current = id;
    dispatch({ type: "LOADING" });
    getResume(id)
      .then(async (resume) => {
        // If re-entering a finalized resume in edit mode, reopen it first
        // so chat is unlocked and a fresh turn allocation is granted.
        if (mode === "edit" && resume.is_finalized) {
          try {
            await reopenResume(resume.id || id);
          } catch {
            // If reopen fails (e.g. network), continue loading read-only
          }
        }

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
          chatHistory: (resume.chat_history || []).slice(-10),
          isFinalized: false,
        });
      })
      .catch(() => {
        loadedIdRef.current = null;
        navigate("/dashboard");
      });
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (state.phase === "DONE") {
      refreshResumes();
    }
  }, [state.phase]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleGenerateDraft = useCallback(
    async ({ jobTitle = "", company = "" } = {}) => {
      if (state.jobDescription.trim().length < 10) {
        dispatch({
          type: "ERROR",
          message:
            "Please paste a job description before generating your draft.",
        });
        return;
      }
      dispatch({ type: "DRAFT_STARTED" });
      try {
        const response = await generateDraft(
          state.resumeId,
          state.jobDescription,
          jobTitle,
          company,
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
    },
    [state.resumeId, state.jobDescription],
  );

  const handleChatSend = useCallback(
    async (message) => {
      dispatch({ type: "CHAT_SENT", message });
      dispatch({ type: "CHAT_SENDING" });
      try {
        const response = await sendChatMessage(state.resumeId, message);
        dispatch({ type: "CHAT_RECEIVED", reply: response.assistant_reply });
        if (state.phase === "FINALIZING") {
          dispatch({ type: "AI_SUGGESTIONS_RECEIVED", roles: response.roles });
        } else {
          dispatch({
            type: "CHAT_UPDATED",
            roles: response.roles,
            civilian_title: response.civilian_title,
            summary: response.summary,
          });
        }
      } catch (err) {
        if (err.status === 409) {
          dispatch({ type: "CHAT_FAILED", message: "" });
          throw err;
        }
        dispatch({ type: "CHAT_FAILED", message: err.message });
      } finally {
        dispatch({ type: "CHAT_DONE_SENDING" });
      }
    },
    [state.resumeId, state.phase],
  );

  return {
    state,
    dispatch,
    handleGenerateDraft,
    handleChatSend,
  };
}
