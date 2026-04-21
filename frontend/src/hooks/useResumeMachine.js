import { useReducer, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { generateDraft, sendChatMessage, getResume } from "../api/resumes";
import { useResumes } from "../context/ResumeContext";

const initialState = {
  phase: "IDLE", // IDLE | LOADING | UPLOADED | DRAFTING | REVIEWING | FINALIZING | DONE
  resumeId: null,
  jobDescription: "",
  draft: null, // { civilian_title, summary, roles[] }
  aiInitialDraft: null, // frozen snapshot of roles[] from DRAFT_RECEIVED — never overwritten
  chatHistory: [], // display-only — [{ role, content }] — NOT sent to backend
  aiSuggestions: null, // roles[] from chat response when phase === FINALIZING
  bulletFlags: [], // [{ role_index, bullet_index, flags[] }] from backend grounding validator
  summaryFlags: [],
  isSending: false,
  chatTurnCount: 0,
  isFinalized: false,
  tailorLimitHit: false, // true when backend returns 403 TAILOR_LIMIT_REACHED — survives phase transitions
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
        bulletFlags: action.bulletFlags || [],
        summaryFlags: action.summaryFlags || [],
      };
    case "DRAFT_FAILED":
      return { ...state, phase: "UPLOADED", error: action.message };
    case "TAILOR_LIMIT_HIT":
      return { ...state, phase: "UPLOADED", tailorLimitHit: true, error: "" };
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
        bulletFlags: action.bulletFlags ?? state.bulletFlags,
        summaryFlags: action.summaryFlags ?? state.summaryFlags,
      };
    case "CHAT_FAILED":
      // Pop the optimistically-added user message and set error
      return {
        ...state,
        chatHistory: state.chatHistory.slice(0, -1),
        error: action.message,
      };
    case "AI_SUGGESTIONS_RECEIVED":
      return {
        ...state,
        aiSuggestions: action.roles,
        bulletFlags: action.bulletFlags ?? state.bulletFlags,
        summaryFlags: action.summaryFlags ?? state.summaryFlags,
      };
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
        chatTurnCount: action.chatTurnCount || 0,
        isFinalized: action.isFinalized || false,
        summaryFlags: action.summaryFlags || [],
        error: null,
      };
    case "CHAT_SENDING":
      return { ...state, isSending: true };
    case "CHAT_DONE_SENDING":
      return { ...state, isSending: false };
    case "CHAT_TURN_INCREMENTED":
      return { ...state, chatTurnCount: state.chatTurnCount + 1 };
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
  const isNew = searchParams.get("new") === "1";

  // Resume re-entry from Dashboard — re-runs whenever ?id or ?new changes.
  // Handles three paths:
  //   1. ?new=1              — explicit "start fresh" intent from + NEW RESUME.
  //                            Reset state and strip the flag from URL.
  //   2. no id, no new       — bare /resume-builder visit. Reset if any
  //                            prior resume was loaded in this hook instance.
  //   3. ?id=<uuid>          — load that resume from DB into the state machine.
  useEffect(() => {
    // Path 1: explicit new-resume intent
    if (isNew) {
      loadedIdRef.current = null;
      dispatch({ type: "RESET" });
      // Strip ?new=1 so browser refresh does not re-trigger and so the
      // URL returns to the canonical /resume-builder form.
      navigate("/resume-builder", { replace: true });
      return;
    }

    // Path 2: bare /resume-builder with no id
    if (!id) {
      // Always reset when landing here without an id. RESET is a no-op
      // when state is already initial, so this is safe. Dropping the
      // prior `loadedIdRef.current !== null` guard prevents the stale-
      // draft bug when AppShell keeps ResumeBuilder mounted across
      // navigations.
      loadedIdRef.current = null;
      dispatch({ type: "RESET" });
      return;
    }

    // Path 3: load an existing resume
    if (loadedIdRef.current === id) return; // already loaded this resume

    loadedIdRef.current = id;
    dispatch({ type: "LOADING" });
    getResume(id)
      .then((resume) => {
        // Note: reopen (is_finalized True -> False) is handled by the
        // caller (Dashboard Edit button) before navigation, not here.
        // This effect only LOADS; it never mutates server state.

        // Pre-draft orphan: PDF uploaded but draft never generated
        // (roles empty AND no session anchor). Route to UPLOADED phase
        // so UploadForm renders with the PDF already attached and the
        // user can paste a JD + click GENERATE to finish.
        const hasDraft =
          (resume.roles && resume.roles.length > 0) ||
          resume.session_anchor != null;

        let resolvedPhase;
        if (!hasDraft) {
          resolvedPhase = "UPLOADED";
        } else if (mode === "edit") {
          resolvedPhase = "FINALIZING";
        } else {
          resolvedPhase = "REVIEWING";
        }

        dispatch({
          type: "RESUME_LOADED",
          resumeId: resume.id || id,
          phase: resolvedPhase,
          draft: {
            civilian_title: resume.civilian_title,
            summary: resume.summary,
            roles: resume.roles || [],
          },
          aiInitialDraft: resume.ai_initial_draft || resume.roles || [],
          chatHistory: (resume.chat_history || []).slice(-10),
          chatTurnCount: resume.chat_turn_count || 0,
          isFinalized: resume.is_finalized || false,
        });
      })
      .catch(() => {
        loadedIdRef.current = null;
        navigate("/dashboard");
      });
  }, [id, isNew]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // Refresh Dashboard's cached resume list whenever a phase transition
    // materially changes a row's status on Dashboard:
    //   UPLOADED   — new orphan just created (appears as UNTITLED / UPLOADED)
    //   REVIEWING  — draft just landed (UPLOADED → IN PROGRESS, title set)
    //   DONE       — finalize just landed (IN PROGRESS → FINALIZED)
    // Without this, users must hard-refresh Dashboard to see new work.
    if (
      state.phase === "UPLOADED" ||
      state.phase === "REVIEWING" ||
      state.phase === "DONE"
    ) {
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
          bulletFlags: response.bullet_flags || [],
          summaryFlags: response.summary_flags || [],
        });
      } catch (err) {
        if (err.status === 403 && err.data?.code === "TAILOR_LIMIT_REACHED") {
          // Set a persistent flag on the machine instead of re-throwing.
          // The re-throw approach fails here because DRAFT_FAILED would
          // unmount UploadForm (phase DRAFTING -> UPLOADED) before its
          // catch handler runs, discarding any local setState calls.
          dispatch({ type: "TAILOR_LIMIT_HIT" });
          return;
        }
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
        dispatch({ type: "CHAT_TURN_INCREMENTED" });
        if (state.phase === "FINALIZING") {
          dispatch({
            type: "AI_SUGGESTIONS_RECEIVED",
            roles: response.roles,
            bulletFlags: response.bullet_flags,
            summaryFlags: response.summary_flags,
          });
        } else {
          dispatch({
            type: "CHAT_UPDATED",
            roles: response.roles,
            civilian_title: response.civilian_title,
            summary: response.summary,
            bulletFlags: response.bullet_flags,
            summaryFlags: response.summary_flags,
          });
        }
      } catch (err) {
        if (err.status === 409) {
          dispatch({ type: "CHAT_FAILED", message: "" });
          throw err;
        }
        if (err.status === 403 && err.data?.code === "CHAT_LIMIT_REACHED") {
          // Pop the optimistic message, don't set a banner — ChatPane's
          // own catch handler sets lockedMsg + opens the Upgrade modal.
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
    bulletFlags: state.bulletFlags,
    summaryFlags: state.summaryFlags,
  };
}
