# Phase 4 Frontend Design — RankToRole Resume Builder

**Date:** 2026-04-07
**Scope:** Additive frontend build for the Phase 4 PDF flow. Old `/translator` page and all existing components are untouched.

---

## Context

Phases 1–3 delivered auth, models, and a quick text-paste translator (`/translator`). Phase 4 adds a full PDF-first resume builder at `/resume-builder` — a new page with a 6-state flow: upload PDF → generate draft → refine via chat → finalize.

The backend for Phase 4 was completed in Phase 4A. Four endpoints are live:

- `POST /api/v1/resumes/upload/`
- `POST /api/v1/resumes/{id}/draft/`
- `POST /api/v1/resumes/{id}/chat/`
- `PATCH /api/v1/resumes/{id}/finalize/`

---

## Files

### New Files

| File                                     | Responsibility                                                  |
| ---------------------------------------- | --------------------------------------------------------------- |
| `frontend/src/api/resumes.js`            | All 4 API calls for the new flow                                |
| `frontend/src/pages/ResumeBuilder.jsx`   | Page owner — state machine via `useReducer`, all dispatch calls |
| `frontend/src/components/SplitPane.jsx`  | Pure layout wrapper: 2-col grid on desktop, stacked on mobile   |
| `frontend/src/components/DraftPane.jsx`  | Left pane — read-only in REVIEWING, editable in FINALIZING      |
| `frontend/src/components/ChatPane.jsx`   | Right pane — clarifying questions + refinement chat             |
| `frontend/src/components/UploadForm.jsx` | PDF file input + JD textarea, shown in IDLE/UPLOADED phases     |

### Modified Files

| File                               | Change                                                         |
| ---------------------------------- | -------------------------------------------------------------- |
| `frontend/src/App.jsx`             | Add lazy `/resume-builder` route                               |
| `frontend/src/pages/Dashboard.jsx` | Add "Open Builder" link + `is_finalized` badge on resume cards |

### Untouched Files

`TranslateForm.jsx`, `ResumeOutput.jsx`, `Translator.jsx`, `TranslationView` (backend), all auth/nav components, `client.js`.

---

## API Layer (`resumes.js`)

All functions use the existing `client.js` instance. No hardcoded URLs.

```js
uploadResume(file)
  → POST /api/v1/resumes/upload/  [multipart/form-data]
  → returns { id, created_at }
  // frontend extracts id, ignores created_at

generateDraft(resumeId, jobDescription)
  → POST /api/v1/resumes/{id}/draft/  [JSON: { job_description }]
  → returns { civilian_title, summary, bullets, clarifying_questions }

sendChatMessage(resumeId, message, history)
  → POST /api/v1/resumes/{id}/chat/  [JSON: { message, history }]
  → returns { civilian_title, summary, bullets, assistant_reply }

finalizeResume(resumeId, { civilian_title, summary, bullets })
  → PATCH /api/v1/resumes/{id}/finalize/  [JSON]
  → returns finalized Resume
```

`history` is `[{ role, content }]` — the chatHistory array snapshot taken **before** the current message is appended (see ChatPane handler below).

---

## State Machine

### Phases

```
IDLE → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE
```

| Phase      | What the user sees                                                          |
| ---------- | --------------------------------------------------------------------------- |
| IDLE       | UploadForm: PDF input + JD textarea + Upload button                         |
| UPLOADED   | UploadForm with file input disabled + "Generate Draft" button               |
| DRAFTING   | Loading state while `/draft/` runs                                          |
| REVIEWING  | SplitPane: DraftPane (left, read-only) + ChatPane (right, questions + chat) |
| FINALIZING | SplitPane: DraftPane (left, fields editable) + ChatPane (right, locked)     |
| DONE       | Success message + "Back to Dashboard" link                                  |

### Reducer (use exactly — do not rename action types)

```js
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
```

### Handler Skeletons (use exactly — do not move mapping logic into API layer)

**Draft handler** (in `ResumeBuilder.jsx`):

```js
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
    dispatch({ type: "ERROR", message: err.message });
  }
}
```

**Chat send handler** (in `ChatPane.jsx`):

```js
// Pass history snapshot taken BEFORE the new message is appended
const historyBeforeSend = [...chatHistory];
dispatch({ type: "CHAT_SENT", message });
const response = await sendChatMessage(resumeId, message, historyBeforeSend);
dispatch({
  type: "CHAT_RECEIVED",
  draft: response,
  reply: response.assistant_reply,
});
```

---

## Component Behavior

### `UploadForm.jsx`

- Props: `state` (phase, jobDescription), `dispatch`
- PDF file input (`accept=".pdf"`), JD textarea, Upload button
- Client-side: validate `.pdf` extension before calling the API
- On Upload click: calls `uploadResume(file)`, dispatches `UPLOADED` with `resumeId`
- In UPLOADED phase: file input is disabled, "Generate Draft" button appears, JD textarea stays editable
- "Generate Draft" button calls `handleGenerateDraft` (defined in `ResumeBuilder.jsx`, passed as prop)

### `DraftPane.jsx`

- Props: `draft`, `phase`, `dispatch`, `resumeId`
- REVIEWING: read-only `civilian_title`, `summary`, bullet list. No internal state. "Approve & Finalize" button dispatches `FINALIZE_STARTED`
- FINALIZING: component initializes local state (`editTitle`, `editSummary`, `editBullets`) from `draft` props on mount/phase change. Each field becomes editable (`<input>`, `<textarea>`, per-bullet `<textarea>`). "Confirm Final" calls `finalizeResume(resumeId, { civilian_title: editTitle, summary: editSummary, bullets: editBullets })`, then dispatches `DONE`

### `ChatPane.jsx`

- Props: `chatHistory`, `resumeId`, `phase`, `dispatch`
- Renders `chatHistory` as chat bubbles: assistant = gray/left, user = blue/right
- Text input + Send button at bottom
- Send handler uses the snapshot pattern (see above): snapshot history before dispatch, then dispatch `CHAT_SENT`, then call API, then dispatch `CHAT_RECEIVED`
- If backend returns 409: lock input, show "Resume finalized" message
- In FINALIZING/DONE phases: input is locked

### `SplitPane.jsx`

- Pure layout, no logic
- `md:grid-cols-2` with visible vertical divider
- Mobile: stacked (draft on top, chat below)
- Props: `left`, `right` (React children)

---

## Dashboard Changes

Two additions to `Dashboard.jsx`, no other changes:

1. **"Open Builder" link** — in the page header alongside "New Translation". Routes to `/resume-builder`. Same `bg-blue-700` button style.

2. **`is_finalized` badge** — on cards where `t.is_finalized === true`:
   ```jsx
   <span className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">
     Finalized
   </span>
   ```
   Positioned inline next to `civilian_title`.

---

## Styling

- Tailwind only — no new CSS files
- Match existing app: `blue-700` primary, `gray-50` backgrounds, `rounded-xl` cards, `shadow-sm`
- No mobile-specific behavior beyond the SplitPane stacking rule

---

## Constraints

- Do not touch any backend file
- Do not modify: `AuthContext.jsx`, `ProtectedRoute.jsx`, `NavBar.jsx`, `Login.jsx`, `Register.jsx`, `Contacts.jsx`, `client.js`, `TranslateForm.jsx`, `ResumeOutput.jsx`, `Translator.jsx`
- No hardcoded URLs — use `client.js` for all requests
- No new packages
