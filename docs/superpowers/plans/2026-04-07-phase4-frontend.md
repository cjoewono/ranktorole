# Phase 4 Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `/resume-builder` page — a 6-phase PDF-first resume builder (upload → draft → chat → finalize) — as a fully additive feature alongside the existing `/translator` page.

**Architecture:** A `useReducer` state machine in `ResumeBuilder.jsx` drives all state transitions. Four child components (`UploadForm`, `DraftPane`, `ChatPane`, `SplitPane`) receive state slices and dispatch as props. The API layer in `resumes.js` wraps the four Phase 4 backend endpoints using the existing `apiFetch` from `client.js`.

**Tech Stack:** React 18, Vite, Tailwind CSS, React Router DOM, existing `apiFetch` from `frontend/src/api/client.js`

---

## File Map

| Action | Path                                     | Responsibility                                             |
| ------ | ---------------------------------------- | ---------------------------------------------------------- |
| Create | `frontend/src/api/resumes.js`            | 4 API functions for Phase 4 endpoints                      |
| Create | `frontend/src/components/SplitPane.jsx`  | Pure 2-col layout (desktop) / stacked (mobile)             |
| Create | `frontend/src/components/UploadForm.jsx` | PDF input + JD textarea — IDLE and UPLOADED phases         |
| Create | `frontend/src/components/DraftPane.jsx`  | Resume display (REVIEWING) and inline editing (FINALIZING) |
| Create | `frontend/src/components/ChatPane.jsx`   | Chat bubble list + send input                              |
| Create | `frontend/src/pages/ResumeBuilder.jsx`   | Page owner — `useReducer` state machine, all handlers      |
| Modify | `frontend/src/App.jsx`                   | Add lazy `/resume-builder` route                           |
| Modify | `frontend/src/pages/Dashboard.jsx`       | Add "Open Builder" link + `is_finalized` badge on cards    |

**Untouched (do not modify):** `client.js`, `AuthContext.jsx`, `ProtectedRoute.jsx`, `NavBar.jsx`, `Login.jsx`, `Register.jsx`, `Contacts.jsx`, `TranslateForm.jsx`, `ResumeOutput.jsx`, `Translator.jsx`, all backend files.

---

## Task 1: API Layer

**Files:**

- Create: `frontend/src/api/resumes.js`

- [ ] **Step 1: Create `resumes.js`**

```js
import { apiFetch } from "./client";

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);
  // Pass Content-Type: undefined so apiFetch's default "application/json" is
  // overridden — browser then sets multipart/form-data with correct boundary.
  const res = await apiFetch("/api/v1/resumes/upload/", {
    method: "POST",
    headers: { "Content-Type": undefined },
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Upload failed");
  return data; // { id, created_at }
}

export async function generateDraft(resumeId, jobDescription) {
  const res = await apiFetch(`/api/v1/resumes/${resumeId}/draft/`, {
    method: "POST",
    body: JSON.stringify({ job_description: jobDescription }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Draft generation failed");
  return data; // { civilian_title, summary, bullets, clarifying_questions }
}

export async function sendChatMessage(resumeId, message, history) {
  const res = await apiFetch(`/api/v1/resumes/${resumeId}/chat/`, {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Chat request failed");
  return data; // { civilian_title, summary, bullets, assistant_reply }
}

export async function finalizeResume(
  resumeId,
  { civilian_title, summary, bullets },
) {
  const res = await apiFetch(`/api/v1/resumes/${resumeId}/finalize/`, {
    method: "PATCH",
    body: JSON.stringify({ civilian_title, summary, bullets }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Finalize failed");
  return data; // full Resume object
}
```

- [ ] **Step 2: Verify build**

```bash
docker compose exec frontend npm run build
```

Expected: exits 0 with no TypeErrors or missing-module errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/resumes.js
git commit -m "feat: add resumes API layer (Phase 4)"
```

---

## Task 2: SplitPane Layout Component

**Files:**

- Create: `frontend/src/components/SplitPane.jsx`

- [ ] **Step 1: Create `SplitPane.jsx`**

```jsx
export default function SplitPane({ left, right }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-0 md:divide-x md:divide-gray-200">
      <div className="min-w-0 p-4 md:pr-6">{left}</div>
      <div className="min-w-0 p-4 md:pl-6">{right}</div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
docker compose exec frontend npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SplitPane.jsx
git commit -m "feat: add SplitPane layout component"
```

---

## Task 3: UploadForm Component

**Files:**

- Create: `frontend/src/components/UploadForm.jsx`

- [ ] **Step 1: Create `UploadForm.jsx`**

```jsx
import { useState } from "react";
import { uploadResume } from "../api/resumes";

export default function UploadForm({ state, dispatch, onGenerateDraft }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const isUploaded = state.phase === "UPLOADED";

  async function handleUpload() {
    if (!file) return;
    if (!file.name.endsWith(".pdf")) {
      dispatch({ type: "ERROR", message: "Only PDF files are accepted." });
      return;
    }
    setUploading(true);
    try {
      const result = await uploadResume(file);
      dispatch({ type: "UPLOADED", resumeId: result.id });
    } catch (err) {
      dispatch({ type: "ERROR", message: err.message });
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
      <h2 className="font-semibold text-gray-800 text-lg">
        Upload Your Resume
      </h2>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Resume PDF
        </label>
        <input
          type="file"
          accept=".pdf"
          disabled={isUploaded}
          onChange={(e) => setFile(e.target.files[0] || null)}
          className="block w-full text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Job Description
        </label>
        <textarea
          rows={6}
          value={state.jobDescription}
          onChange={(e) =>
            dispatch({ type: "JD_CHANGED", value: e.target.value })
          }
          placeholder="Paste the job description here..."
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
      </div>

      {state.error && <p className="text-red-600 text-sm">{state.error}</p>}

      {!isUploaded ? (
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
        >
          {uploading ? "Uploading..." : "Upload PDF"}
        </button>
      ) : (
        <div className="flex items-center gap-4">
          <span className="text-green-700 text-sm font-medium">
            ✓ PDF uploaded
          </span>
          <button
            onClick={onGenerateDraft}
            disabled={!state.jobDescription.trim()}
            className="bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
          >
            Generate Draft
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
docker compose exec frontend npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/UploadForm.jsx
git commit -m "feat: add UploadForm component"
```

---

## Task 4: DraftPane Component

**Files:**

- Create: `frontend/src/components/DraftPane.jsx`

- [ ] **Step 1: Create `DraftPane.jsx`**

The key implementation detail: FINALIZING phase uses a separate `FinalizingEditor` sub-component rendered conditionally. This guarantees `useState` initializes from current `draft` props on fresh mount (after any chat refinements), rather than from stale initial values.

```jsx
import { useState } from "react";
import { finalizeResume } from "../api/resumes";

function FinalizingEditor({ draft, resumeId, dispatch }) {
  const [editTitle, setEditTitle] = useState(draft.civilian_title);
  const [editSummary, setEditSummary] = useState(draft.summary);
  const [editBullets, setEditBullets] = useState([...draft.bullets]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleConfirm() {
    setSaving(true);
    setError(null);
    try {
      await finalizeResume(resumeId, {
        civilian_title: editTitle,
        summary: editSummary,
        bullets: editBullets,
      });
      dispatch({ type: "DONE" });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">
        Edit & Finalize
      </h2>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">
          Title
        </label>
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">
          Summary
        </label>
        <textarea
          rows={4}
          value={editSummary}
          onChange={(e) => setEditSummary(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">
          Bullets
        </label>
        <div className="space-y-2">
          {editBullets.map((bullet, i) => (
            <textarea
              key={i}
              rows={2}
              value={bullet}
              onChange={(e) => {
                const next = [...editBullets];
                next[i] = e.target.value;
                setEditBullets(next);
              }}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          ))}
        </div>
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <button
        onClick={handleConfirm}
        disabled={saving}
        className="bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
      >
        {saving ? "Saving..." : "Confirm Final"}
      </button>
    </div>
  );
}

export default function DraftPane({ draft, phase, dispatch, resumeId }) {
  if (!draft) return null;

  if (phase === "FINALIZING") {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
        <FinalizingEditor
          draft={draft}
          resumeId={resumeId}
          dispatch={dispatch}
        />
      </div>
    );
  }

  // REVIEWING phase — read-only
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
      <h2 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">
        Draft Resume
      </h2>

      <div>
        <p className="text-xs font-medium text-gray-500 mb-0.5">Title</p>
        <p className="font-semibold text-gray-900">{draft.civilian_title}</p>
      </div>

      <div>
        <p className="text-xs font-medium text-gray-500 mb-0.5">Summary</p>
        <p className="text-sm text-gray-700 leading-relaxed">{draft.summary}</p>
      </div>

      <div>
        <p className="text-xs font-medium text-gray-500 mb-1">Bullets</p>
        <ul className="space-y-1">
          {draft.bullets.map((b, i) => (
            <li key={i} className="text-sm text-gray-700 flex gap-2">
              <span className="text-gray-400 shrink-0">•</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
      </div>

      <button
        onClick={() => dispatch({ type: "FINALIZE_STARTED" })}
        className="bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
      >
        Approve &amp; Finalize
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
docker compose exec frontend npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/DraftPane.jsx
git commit -m "feat: add DraftPane component (reviewing + finalizing)"
```

---

## Task 5: ChatPane Component

**Files:**

- Create: `frontend/src/components/ChatPane.jsx`

- [ ] **Step 1: Create `ChatPane.jsx`**

The history snapshot must be taken **before** `CHAT_SENT` is dispatched. This ensures the backend receives the conversation history without the current message (which the backend appends itself).

```jsx
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
      if (
        err.message.includes("409") ||
        err.message.toLowerCase().includes("finalized")
      ) {
        setLockedMsg("Resume is finalized. No further changes.");
      } else {
        dispatch({ type: "ERROR", message: err.message });
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
```

- [ ] **Step 2: Verify build**

```bash
docker compose exec frontend npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ChatPane.jsx
git commit -m "feat: add ChatPane component"
```

---

## Task 6: ResumeBuilder Page

**Files:**

- Create: `frontend/src/pages/ResumeBuilder.jsx`

- [ ] **Step 1: Create `ResumeBuilder.jsx`**

```jsx
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
      dispatch({ type: "ERROR", message: err.message });
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
```

- [ ] **Step 2: Verify build**

```bash
docker compose exec frontend npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ResumeBuilder.jsx
git commit -m "feat: add ResumeBuilder page with useReducer state machine"
```

---

## Task 7: Wire Route and Update Dashboard

**Files:**

- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/pages/Dashboard.jsx`

- [ ] **Step 1: Add lazy route to `App.jsx`**

In `frontend/src/App.jsx`, add the lazy import after the existing `Contacts` import line:

```jsx
const ResumeBuilder = lazy(() => import("./pages/ResumeBuilder"));
```

Then add the route inside the `<Route element={<ProtectedRoute />}>` block, after the `/contacts` route:

```jsx
<Route path="/resume-builder" element={<ResumeBuilder />} />
```

The full `App.jsx` after changes:

```jsx
import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";

const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Translator = lazy(() => import("./pages/Translator"));
const Contacts = lazy(() => import("./pages/Contacts"));
const ResumeBuilder = lazy(() => import("./pages/ResumeBuilder"));

function Spinner() {
  return (
    <div className="min-h-screen flex items-center justify-center text-gray-400 text-sm">
      Loading...
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<Spinner />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/translator" element={<Translator />} />
              <Route path="/contacts" element={<Contacts />} />
              <Route path="/resume-builder" element={<ResumeBuilder />} />
            </Route>

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
```

- [ ] **Step 2: Update `Dashboard.jsx`**

Two additive changes only:

1. Add "Open Builder" button alongside the existing "New Translation" link in the header.
2. Add `is_finalized` badge next to `civilian_title` on cards where `t.is_finalized === true`.

The full `Dashboard.jsx` after changes:

```jsx
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import NavBar from "../components/NavBar";
import { listTranslations, deleteTranslation } from "../api/translations";

export default function Dashboard() {
  const [translations, setTranslations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    listTranslations()
      .then(setTranslations)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id) {
    try {
      await deleteTranslation(id);
      setTranslations((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">
            Your Translations
          </h1>
          <div className="flex gap-3">
            <Link
              to="/resume-builder"
              className="bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              Open Builder
            </Link>
            <Link
              to="/translator"
              className="bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              New Translation
            </Link>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3 mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center text-gray-400 py-16 text-sm">
            Loading...
          </div>
        ) : translations.length === 0 ? (
          <div className="text-center py-16 space-y-3">
            <p className="text-gray-400 text-sm">No translations yet.</p>
            <Link
              to="/translator"
              className="text-blue-600 text-sm hover:underline"
            >
              Translate your first resume
            </Link>
          </div>
        ) : (
          <ul className="space-y-4">
            {translations.map((t) => (
              <li
                key={t.id}
                className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="font-semibold text-gray-900 truncate">
                        {t.civilian_title}
                      </h2>
                      {t.is_finalized && (
                        <span className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                          Finalized
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                      {t.summary}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">
                      {new Date(t.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDelete(t.id)}
                    className="text-red-400 hover:text-red-600 text-sm shrink-0 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
docker compose exec frontend npm run build
```

Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.jsx frontend/src/pages/Dashboard.jsx
git commit -m "feat: add /resume-builder route and dashboard updates"
```

---

## Task 8: End-to-End Smoke Test

Verify the full flow in a running environment.

- [ ] **Step 1: Start services**

```bash
docker compose up
```

Confirm all services healthy in logs.

- [ ] **Step 2: Run pending migration**

```bash
docker compose exec backend python manage.py migrate
```

Expected: `Running migrations: Applying translate_app.0002_resume_is_finalized... OK`

- [ ] **Step 3: Full flow walkthrough**

Open `http://localhost` in a browser and verify each phase transition:

1. Log in → Dashboard shows "Open Builder" button
2. Click "Open Builder" → `/resume-builder` loads with PDF input + JD textarea
3. Select a PDF → click "Upload PDF" → file input disables, "Generate Draft" appears
4. Paste job description → click "Generate Draft" → loading message appears
5. Draft loads → SplitPane shows draft on left, 2-3 clarifying questions as chat bubbles on right
6. Type a reply in chat → send → assistant reply + updated draft appear
7. Click "Approve & Finalize" → DraftPane switches to editable fields (title/summary/bullets)
8. Edit a bullet → click "Confirm Final" → success screen with "Back to Dashboard" link
9. Click "Back to Dashboard" → finalized resume card shows green "Finalized" badge

- [ ] **Step 4: Verify 409 lock**

With a finalized resume ID, attempt to call the chat endpoint directly (or trigger via a second browser tab still on the REVIEWING phase). Confirm ChatPane shows "Resume is finalized." and locks the input.

- [ ] **Step 5: Verify mobile layout**

Resize browser to mobile width. Confirm SplitPane stacks vertically (draft above, chat below).
