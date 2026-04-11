# SPA Layout, Chat UX & Finalize/Export Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the React frontend into a true SPA with a persistent shell (no page flicker, no state loss on navigation), uniform page layout via a shared `PageHeader` component, a chat loading indicator, and an unambiguous Confirm → Export finalize flow.

**Architecture:** A single `AppShell` in `App.jsx` renders `NavBar` once and keeps all three protected pages always mounted, using Tailwind's `hidden` (`display: none`) to hide inactive ones. `AppShell` holds a `fullscreen` boolean that `ResumeBuilder` toggles via a `setFullscreen` prop to add `overflow-hidden` during split-pane mode. Chat loading state (`isSending`) lives in `useResumeMachine` and flows down to `ChatPane`. The `DONE` phase is added to the split-pane phases so the export CTA appears only after finalization — inside the left pane.

**Tech Stack:** React 18, React Router DOM v6, Tailwind CSS (existing design tokens), jsPDF (existing `exportPDF` utility)

---

## File Map

| File                                                     | Action | Responsibility                                                                                                   |
| -------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------- |
| `frontend/src/App.jsx`                                   | Modify | Replace per-page Routes with AppShell; always-mounted pages; fullscreen state                                    |
| `frontend/src/components/ProtectedRoute.jsx`             | Delete | No longer needed — AppShell handles auth                                                                         |
| `frontend/src/components/PageHeader.jsx`                 | Create | Shared header: status chip + headline + optional action button                                                   |
| `frontend/src/pages/Dashboard.jsx`                       | Modify | Remove NavBar/outer wrapper; use PageHeader                                                                      |
| `frontend/src/pages/Contacts.jsx`                        | Modify | Remove NavBar/outer wrapper; use PageHeader                                                                      |
| `frontend/src/pages/ResumeBuilder.jsx`                   | Modify | Remove NavBar/outer wrapper; accept `setFullscreen` prop; add DONE to split phases; use PageHeader for init view |
| `frontend/src/hooks/useResumeMachine.js`                 | Modify | Add `isSending` to state; dispatch CHAT_SENDING/CHAT_DONE_SENDING in handleChatSend                              |
| `frontend/src/components/ChatPane.jsx`                   | Modify | Replace local `sending` state with `isSending` prop; add thinking bubble; update DONE lock label                 |
| `frontend/src/components/DraftPane/FinalizingEditor.jsx` | Modify | Remove Export PDF button; move title into header row                                                             |
| `frontend/src/components/DraftPane/index.jsx`            | Modify | Add DONE phase overlay: Export PDF + Back to Dashboard                                                           |

---

## Task 1: AppShell — Persistent shell with always-mounted pages

**Files:**

- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Replace App.jsx with the AppShell implementation**

Full file replacement — `frontend/src/App.jsx`:

```jsx
import { lazy, Suspense, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ResumeProvider } from "./context/ResumeContext";
import NavBar from "./components/NavBar";

const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Contacts = lazy(() => import("./pages/Contacts"));
const ResumeBuilder = lazy(() => import("./pages/ResumeBuilder"));

function Spinner() {
  return (
    <div className="min-h-screen flex items-center justify-center text-on-surface-variant font-label text-xs tracking-widest uppercase">
      Loading...
    </div>
  );
}

function AppShell() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const [fullscreen, setFullscreen] = useState(false);

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const path = location.pathname;

  return (
    <div
      className={`min-h-screen bg-background${fullscreen ? " overflow-hidden" : ""}`}
    >
      <NavBar />
      <div className={path === "/dashboard" ? "pb-20 md:pb-0" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <Dashboard />
        </Suspense>
      </div>
      <div className={path === "/contacts" ? "pb-20 md:pb-0" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <Contacts />
        </Suspense>
      </div>
      <div className={path === "/resume-builder" ? "" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <ResumeBuilder setFullscreen={setFullscreen} />
        </Suspense>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ResumeProvider>
          <Suspense fallback={<Spinner />}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="*" element={<AppShell />} />
            </Routes>
          </Suspense>
        </ResumeProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
```

- [ ] **Step 2: Verify build passes**

```bash
docker compose exec frontend npm run build
```

Expected: build completes with no errors. (Pages still contain their own NavBar at this point — that's fixed in Task 3.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add AppShell with always-mounted pages and persistent NavBar"
```

---

## Task 2: PageHeader shared component

**Files:**

- Create: `frontend/src/components/PageHeader.jsx`

- [ ] **Step 1: Create PageHeader.jsx**

Full file — `frontend/src/components/PageHeader.jsx`:

```jsx
export default function PageHeader({ label, title, action }) {
  return (
    <div className="bg-surface-container-low px-4 pt-4 pb-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
        <span className="font-label text-xs tracking-widest uppercase text-secondary">
          {label}
        </span>
      </div>
      <div className="flex items-start justify-between gap-4">
        <h1 className="font-headline font-bold text-4xl uppercase text-on-surface leading-tight">
          {title}
        </h1>
        {action && <div className="shrink-0 mt-1">{action}</div>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build passes**

```bash
docker compose exec frontend npm run build
```

Expected: build completes with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PageHeader.jsx
git commit -m "feat: add PageHeader shared component"
```

---

## Task 3: Refactor pages — remove NavBar/wrapper, use PageHeader

**Files:**

- Modify: `frontend/src/pages/Dashboard.jsx`
- Modify: `frontend/src/pages/Contacts.jsx`
- Modify: `frontend/src/pages/ResumeBuilder.jsx`
- Delete: `frontend/src/components/ProtectedRoute.jsx`

- [ ] **Step 1: Replace Dashboard.jsx**

Full file replacement — `frontend/src/pages/Dashboard.jsx`:

```jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { deleteTranslation } from "../api/translations";
import { useResumes } from "../context/ResumeContext";

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function StatusBadge({ resume }) {
  if (resume.is_finalized) {
    return (
      <span className="bg-secondary/10 text-secondary font-label text-xs tracking-widest uppercase px-3 py-1 rounded-sm">
        FINALIZED
      </span>
    );
  }
  if (resume.roles?.length > 0) {
    return (
      <span className="bg-primary/10 text-primary font-label text-xs tracking-widest uppercase px-3 py-1 rounded-sm">
        IN PROGRESS
      </span>
    );
  }
  return (
    <span className="bg-surface-container-highest text-on-surface-variant font-label text-xs tracking-widest uppercase px-3 py-1 rounded-sm">
      NOT STARTED
    </span>
  );
}

export default function Dashboard() {
  const { resumes, loading, refreshResumes } = useResumes();
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  async function handleDelete(id) {
    try {
      await deleteTranslation(id);
      await refreshResumes();
    } catch (err) {
      setError(err.message);
    }
  }

  function handleNewResume() {
    const inProgress = resumes.find((r) => r.is_finalized === false);
    if (inProgress) {
      navigate(`/resume-builder?id=${inProgress.id}&mode=continue`);
    } else {
      navigate("/resume-builder");
    }
  }

  const finalized = resumes.filter((r) => r.is_finalized).length;
  const inProgress = resumes.filter(
    (r) => !r.is_finalized && (r.roles?.length ?? 0) > 0,
  ).length;

  return (
    <>
      <PageHeader
        label="SYSTEM ACTIVE / CORE_OPERATIONS"
        title={
          <>
            YOUR
            <br />
            DEPLOYMENTS
          </>
        }
        action={
          <button
            onClick={handleNewResume}
            className="mission-gradient font-label text-xs tracking-widest font-semibold uppercase text-on-primary px-4 py-2.5 rounded-md transition-opacity hover:opacity-90"
          >
            + NEW RESUME
          </button>
        }
      />

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {error && (
          <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3">
            {error}
          </div>
        )}

        <div className="grid grid-cols-3 gap-3">
          <div className="bg-surface-container-low p-4">
            <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
              Total
            </p>
            <p className="font-headline font-bold text-4xl text-on-surface">
              {resumes.length}
            </p>
          </div>
          <div className="bg-surface-container-low p-4">
            <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
              Finalized
            </p>
            <p className="font-headline font-bold text-4xl text-secondary">
              {finalized}
            </p>
          </div>
          <div className="bg-surface-container-low p-4">
            <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
              In Progress
            </p>
            <p className="font-headline font-bold text-4xl text-primary">
              {inProgress}
            </p>
          </div>
        </div>

        {loading ? (
          <div className="text-center text-on-surface-variant py-16 font-label text-xs tracking-widest uppercase">
            LOADING DEPLOYMENTS...
          </div>
        ) : resumes.length === 0 ? (
          <div className="text-center py-16 space-y-3">
            <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
              No deployments yet.
            </p>
            <Link
              to="/resume-builder"
              className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
            >
              BUILD YOUR FIRST RESUME
            </Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {resumes.map((resume) => (
              <li key={resume.id} className="bg-surface-container p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 min-w-0 flex-1">
                    <div className="shrink-0 w-8 h-10 bg-surface-container-highest rounded-sm flex items-center justify-center mt-0.5">
                      <span className="text-on-surface-variant text-xs">▤</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        {resume.civilian_title ? (
                          <h2 className="font-headline font-semibold text-on-surface uppercase truncate">
                            {resume.civilian_title}
                          </h2>
                        ) : (
                          <h2 className="font-headline font-semibold text-on-surface-variant uppercase italic truncate">
                            UNTITLED RESUME
                          </h2>
                        )}
                        <StatusBadge resume={resume} />
                      </div>
                      {resume.summary && (
                        <p className="font-body text-sm text-on-surface-variant truncate">
                          {resume.summary}
                        </p>
                      )}
                      <p className="font-label text-xs tracking-widest uppercase text-outline mt-2">
                        {formatDate(resume.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <button
                      onClick={() =>
                        navigate(
                          resume.is_finalized
                            ? `/resume-builder?id=${resume.id}&mode=edit`
                            : `/resume-builder?id=${resume.id}&mode=continue`,
                        )
                      }
                      className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
                    >
                      {resume.is_finalized ? "EDIT & EXPORT" : "CONTINUE"}
                    </button>
                    <button
                      onClick={() => handleDelete(resume.id)}
                      className="font-label text-xs tracking-widest uppercase text-error hover:opacity-80 transition-opacity"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
```

- [ ] **Step 2: Replace Contacts.jsx**

Full file replacement — `frontend/src/pages/Contacts.jsx`:

```jsx
import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import {
  listContacts,
  createContact,
  updateContact,
  deleteContact,
} from "../api/contacts";

const EMPTY_FORM = { name: "", email: "", notes: "" };

export default function Contacts() {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    listContacts()
      .then(setContacts)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  function startEdit(contact) {
    setEditingId(contact.id);
    setForm({
      name: contact.name,
      email: contact.email || "",
      notes: contact.notes || "",
    });
    setShowForm(true);
  }

  function cancelForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setShowForm(false);
    setError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (editingId) {
        const updated = await updateContact(editingId, form);
        setContacts((prev) =>
          prev.map((c) => (c.id === editingId ? updated : c)),
        );
      } else {
        const created = await createContact(form);
        setContacts((prev) => [...prev, created]);
      }
      cancelForm();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteContact(id);
      setContacts((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <PageHeader
        label="INTEL DATABASE / ACTIVE"
        title="OPERATOR INTEL"
        action={
          !showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="mission-gradient font-label text-xs tracking-widest uppercase text-on-primary px-4 py-2.5 rounded-md hover:opacity-90 transition-opacity"
            >
              + ADD CONTACT
            </button>
          )
        }
      />

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        {error && (
          <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3">
            {error}
          </div>
        )}

        {showForm && (
          <div className="bg-surface-container-low p-6">
            <h2 className="font-headline font-semibold text-on-surface uppercase text-sm tracking-wide mb-5">
              {editingId ? "EDIT CONTACT" : "NEW CONTACT"}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div>
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    Name <span className="text-error">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="tactical-input"
                  />
                </div>
                <div>
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) =>
                      setForm({ ...form, email: e.target.value })
                    }
                    className="tactical-input"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    Notes
                  </label>
                  <input
                    type="text"
                    value={form.notes}
                    onChange={(e) =>
                      setForm({ ...form, notes: e.target.value })
                    }
                    className="tactical-input"
                  />
                </div>
              </div>
              <div className="flex gap-4 pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="mission-gradient font-label text-xs tracking-widest uppercase text-on-primary px-6 py-2.5 rounded-md disabled:opacity-50 transition-opacity"
                >
                  {saving
                    ? "SAVING..."
                    : editingId
                      ? "SAVE CHANGES"
                      : "ADD CONTACT"}
                </button>
                <button
                  type="button"
                  onClick={cancelForm}
                  className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-on-surface transition-colors px-4 py-2.5"
                >
                  CANCEL
                </button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="text-center text-on-surface-variant py-16 font-label text-xs tracking-widest uppercase">
            LOADING INTEL...
          </div>
        ) : contacts.length === 0 ? (
          <div className="text-center py-16 font-label text-xs tracking-widest uppercase text-on-surface-variant">
            No contacts yet. Add one above.
          </div>
        ) : (
          <ul className="space-y-3">
            {contacts.map((c) => (
              <li
                key={c.id}
                className="bg-surface-container px-5 py-4 flex items-start justify-between gap-4"
              >
                <div className="min-w-0">
                  <p className="font-headline font-semibold text-on-surface">
                    {c.name}
                  </p>
                  {c.email && (
                    <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mt-0.5 truncate">
                      {c.email}
                    </p>
                  )}
                  {c.notes && (
                    <p className="font-body text-xs text-outline mt-1 italic">
                      {c.notes}
                    </p>
                  )}
                </div>
                <div className="flex gap-4 shrink-0">
                  <button
                    onClick={() => startEdit(c)}
                    className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="font-label text-xs tracking-widest uppercase text-error hover:opacity-80 transition-opacity"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
```

- [ ] **Step 3: Replace ResumeBuilder.jsx**

Full file replacement — `frontend/src/pages/ResumeBuilder.jsx`:

```jsx
import { useEffect } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import UploadForm from "../components/UploadForm";
import SplitPane from "../components/SplitPane";
import DraftPane from "../components/DraftPane";
import ChatPane from "../components/ChatPane";
import useResumeMachine from "../hooks/useResumeMachine";

export default function ResumeBuilder({ setFullscreen }) {
  const { state, dispatch, handleGenerateDraft, handleChatSend } =
    useResumeMachine();

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
```

- [ ] **Step 4: Delete ProtectedRoute.jsx (now dead code — AppShell handles auth)**

```bash
rm frontend/src/components/ProtectedRoute.jsx
```

- [ ] **Step 5: Verify build passes**

```bash
docker compose exec frontend npm run build
```

Expected: build completes with no errors. Each page now has a single NavBar (from AppShell) and uniform PageHeader.

- [ ] **Step 6: Confirm backend tests still pass**

```bash
docker compose exec backend pytest --tb=short -q
```

Expected: 77 passed.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Dashboard.jsx frontend/src/pages/Contacts.jsx frontend/src/pages/ResumeBuilder.jsx
git rm frontend/src/components/ProtectedRoute.jsx
git commit -m "refactor: uniform page layout — remove per-page NavBar/wrapper, use PageHeader"
```

---

## Task 4: isSending state + chat loading indicator

**Files:**

- Modify: `frontend/src/hooks/useResumeMachine.js`
- Modify: `frontend/src/components/ChatPane.jsx`

- [ ] **Step 1: Add isSending to useResumeMachine**

Three targeted edits to `frontend/src/hooks/useResumeMachine.js`:

**1a — Add `isSending: false` to `initialState` (after `aiSuggestions: null`):**

```js
const initialState = {
  phase: "IDLE",
  resumeId: null,
  jobDescription: "",
  draft: null,
  aiInitialDraft: null,
  chatHistory: [],
  aiSuggestions: null,
  isSending: false,
  error: null,
};
```

**1b — Add two new reducer cases before `default`:**

```js
case "CHAT_SENDING":
  return { ...state, isSending: true };
case "CHAT_DONE_SENDING":
  return { ...state, isSending: false };
```

**1c — Replace the `handleChatSend` callback:**

```js
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
      dispatch({ type: "CHAT_FAILED", message: err.message });
    } finally {
      dispatch({ type: "CHAT_DONE_SENDING" });
    }
  },
  [state.resumeId, state.phase],
);
```

- [ ] **Step 2: Replace ChatPane.jsx**

Full file replacement — `frontend/src/components/ChatPane.jsx`:

```jsx
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
```

- [ ] **Step 3: Verify build passes**

```bash
docker compose exec frontend npm run build
```

Expected: build completes with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useResumeMachine.js frontend/src/components/ChatPane.jsx
git commit -m "feat: add isSending state and chat thinking bubble indicator"
```

---

## Task 5: Finalize/Export flow — DONE overlay in split pane

**Files:**

- Modify: `frontend/src/components/DraftPane/FinalizingEditor.jsx`
- Modify: `frontend/src/components/DraftPane/index.jsx`

- [ ] **Step 1: Replace FinalizingEditor.jsx — remove Export PDF button, move title into header row**

Full file replacement — `frontend/src/components/DraftPane/FinalizingEditor.jsx`:

```jsx
import { useState } from "react";
import { finalizeResume } from "../../api/resumes";
import BulletEditor from "./BulletEditor";

export default function FinalizingEditor({
  draft,
  aiInitialDraft,
  aiSuggestions,
  resumeId,
  dispatch,
}) {
  if (!draft || !draft.roles) return null;
  const [editTitle, setEditTitle] = useState(draft.civilian_title);
  const [editSummary, setEditSummary] = useState(draft.summary);
  const [editRoles, setEditRoles] = useState(() =>
    (draft.roles || []).map((role) => ({
      ...role,
      bullets: [...role.bullets],
    })),
  );
  const [expandedKey, setExpandedKey] = useState(null);
  const [dismissedSuggestions, setDismissedSuggestions] = useState(
    () => new Set(),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  function handleToggle(roleIdx, bulletIdx) {
    const key = `${roleIdx}-${bulletIdx}`;
    setExpandedKey((prev) => (prev === key ? null : key));
  }

  function handleBulletChange(roleIdx, bulletIdx, val) {
    setEditRoles((prev) =>
      prev.map((role, ri) => {
        if (ri !== roleIdx) return role;
        const bullets = [...role.bullets];
        bullets[bulletIdx] = val;
        return { ...role, bullets };
      }),
    );
  }

  function getSuggestion(roleIdx, bulletIdx) {
    const key = `${roleIdx}-${bulletIdx}`;
    if (dismissedSuggestions.has(key)) return null;
    const suggestedBullet = aiSuggestions?.[roleIdx]?.bullets?.[bulletIdx];
    const currentBullet = editRoles[roleIdx]?.bullets[bulletIdx];
    return suggestedBullet && suggestedBullet !== currentBullet
      ? suggestedBullet
      : null;
  }

  function handleAcceptSuggestion(roleIdx, bulletIdx, suggestion) {
    handleBulletChange(roleIdx, bulletIdx, suggestion);
    setDismissedSuggestions((prev) => {
      const next = new Set(prev);
      next.add(`${roleIdx}-${bulletIdx}`);
      return next;
    });
  }

  function handleDismissSuggestion(roleIdx, bulletIdx) {
    setDismissedSuggestions((prev) => {
      const next = new Set(prev);
      next.add(`${roleIdx}-${bulletIdx}`);
      return next;
    });
  }

  async function handleConfirm() {
    setSaving(true);
    setError(null);
    try {
      await finalizeResume(resumeId, {
        civilian_title: editTitle,
        summary: editSummary,
        roles: editRoles,
      });
      dispatch({ type: "DONE" });
    } catch (err) {
      setError(
        err.data?.civilian_title?.[0] ||
          err.data?.summary?.[0] ||
          err.data?.roles?.[0] ||
          err.message,
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => dispatch({ type: "RETURN_TO_CHAT" })}
          className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
        >
          ← Return to Chat
        </button>
        <h2 className="font-headline font-bold text-xl uppercase text-on-surface tracking-wide">
          Edit &amp; Finalize
        </h2>
      </div>

      {/* Title */}
      <div>
        <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
          Mission Headline
        </label>
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          className="tactical-input"
        />
      </div>

      {/* Summary */}
      <div>
        <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
          Executive Summary
        </label>
        <textarea
          rows={5}
          value={editSummary}
          onChange={(e) => setEditSummary(e.target.value)}
          className="tactical-input resize-y"
        />
      </div>

      {/* Roles */}
      <div className="space-y-4">
        <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
          Mission Roles
        </p>
        {(editRoles || []).map((role, roleIdx) => (
          <div key={roleIdx} className="bg-surface-container p-4 space-y-2">
            <p className="font-headline font-semibold text-on-surface uppercase text-sm">
              {role.title}
            </p>
            <p className="font-label text-xs tracking-widest uppercase text-outline">
              {role.org}
              {role.org && role.dates ? " · " : ""}
              {role.dates}
            </p>
            <div className="space-y-1.5 mt-2">
              {(role.bullets || []).map((bullet, bulletIdx) => {
                const suggestion = getSuggestion(roleIdx, bulletIdx);
                return (
                  <BulletEditor
                    key={bulletIdx}
                    value={bullet}
                    original={
                      aiInitialDraft?.[roleIdx]?.bullets?.[bulletIdx] ?? bullet
                    }
                    expanded={expandedKey === `${roleIdx}-${bulletIdx}`}
                    onToggle={() => handleToggle(roleIdx, bulletIdx)}
                    onChange={(val) =>
                      handleBulletChange(roleIdx, bulletIdx, val)
                    }
                    suggestion={suggestion}
                    onAccept={(s) =>
                      handleAcceptSuggestion(roleIdx, bulletIdx, s)
                    }
                    onDismiss={() =>
                      handleDismissSuggestion(roleIdx, bulletIdx)
                    }
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3">
          {error}
        </div>
      )}

      {/* Sticky confirm */}
      <div className="sticky bottom-0 bg-background pt-2 pb-4">
        <button
          type="button"
          onClick={handleConfirm}
          disabled={saving || editRoles.length === 0}
          className="mission-gradient w-full text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md disabled:opacity-50 transition-opacity"
        >
          {saving ? "SAVING..." : "CONFIRM FINAL"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Replace DraftPane/index.jsx — add DONE overlay**

Full file replacement — `frontend/src/components/DraftPane/index.jsx`:

```jsx
import { Link } from "react-router-dom";
import DiffView from "./DiffView";
import BulletEditor from "./BulletEditor";
import FinalizingEditor from "./FinalizingEditor";
import { exportPDF } from "../../utils/pdfExport";
import { diffWords } from "../../utils/diffWords";

export default function DraftPane({
  draft,
  aiInitialDraft,
  aiSuggestions,
  phase,
  dispatch,
  resumeId,
}) {
  if (!draft) return null;

  // DONE — export CTA only appears after finalization
  if (phase === "DONE") {
    return (
      <div className="bg-surface-container-low p-5 flex flex-col items-center justify-center h-full space-y-6 text-center">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
          <span className="font-label text-xs tracking-widest uppercase text-secondary">
            MISSION COMPLETE
          </span>
        </div>
        <h2 className="font-headline font-bold text-2xl uppercase text-on-surface">
          Resume Finalized
        </h2>
        <div className="w-full space-y-3">
          <button
            type="button"
            onClick={() =>
              exportPDF({
                civilian_title: draft.civilian_title,
                summary: draft.summary,
                roles: draft.roles,
              })
            }
            className="mission-gradient w-full text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md hover:opacity-90 transition-opacity"
          >
            EXPORT PDF
          </button>
          <Link
            to="/dashboard"
            className="block font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors py-2"
          >
            BACK TO DASHBOARD
          </Link>
        </div>
      </div>
    );
  }

  if (phase === "FINALIZING") {
    if (!draft.roles) return null;
    return (
      <div className="bg-surface-container-low p-5">
        <FinalizingEditor
          draft={draft}
          aiInitialDraft={aiInitialDraft}
          aiSuggestions={aiSuggestions}
          resumeId={resumeId}
          dispatch={dispatch}
        />
      </div>
    );
  }

  // REVIEWING phase — read-only role cards
  if (!draft.roles) return null;
  return (
    <div className="bg-surface-container-low p-5 space-y-5">
      <div>
        <h2 className="font-headline font-bold text-2xl uppercase text-on-surface">
          {draft.civilian_title}
        </h2>
        <p className="font-body text-sm text-on-surface-variant leading-relaxed mt-2">
          {draft.summary}
        </p>
      </div>

      {(draft.roles || []).map((role, roleIdx) => (
        <div key={roleIdx} className="bg-surface-container p-4 space-y-2">
          <p className="font-headline font-semibold text-on-surface uppercase text-sm">
            {role.title}
          </p>
          <p className="font-label text-xs tracking-widest uppercase text-outline">
            {role.org}
            {role.org && role.dates ? " · " : ""}
            {role.dates}
          </p>
          <ul className="space-y-1.5 mt-1">
            {(role.bullets || []).map((b, bi) => (
              <li key={bi} className="flex gap-2 pl-2">
                <span className="text-secondary shrink-0 mt-0.5">✓</span>
                <span className="font-body text-sm text-on-surface leading-relaxed">
                  {b}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}

      <button
        type="button"
        onClick={() => dispatch({ type: "FINALIZE_STARTED" })}
        className="mission-gradient w-full text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md hover:opacity-90 transition-opacity"
      >
        Approve &amp; Edit
      </button>
    </div>
  );
}

// Re-export sub-components for direct access if needed
export { DiffView, BulletEditor, FinalizingEditor, exportPDF, diffWords };
```

- [ ] **Step 3: Verify build passes**

```bash
docker compose exec frontend npm run build
```

Expected: build completes with no errors.

- [ ] **Step 4: Confirm backend tests still pass**

```bash
docker compose exec backend pytest --tb=short -q
```

Expected: 77 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DraftPane/FinalizingEditor.jsx frontend/src/components/DraftPane/index.jsx
git commit -m "feat: DONE overlay in split pane — Export PDF only appears after finalization"
```

---

## Smoke Test Checklist

After all tasks complete, verify in the browser (`docker compose up`):

- [ ] Navigate Dashboard → Intel → Dashboard: no page flicker, NavBar never disappears
- [ ] Open Contacts, partially fill in the Add Contact form, navigate to Dashboard and back — form state is preserved
- [ ] NavBar active link highlights correctly on each page
- [ ] Upload a PDF, paste a job description, click "Generate Draft" — split pane appears, chat loads
- [ ] Send a chat message: thinking bubble (`● ● ● PROCESSING REQUEST...`) appears, textarea and SEND button are disabled while processing, both re-enable after response
- [ ] Click "Approve & Edit": FINALIZING view shows no Export PDF button in the header — only "← Return to Chat" and "Edit & Finalize" title
- [ ] Click "Confirm Final": DONE overlay appears in the left pane with "EXPORT PDF" (gradient) and "BACK TO DASHBOARD" (text link); chat pane shows "MISSION COMPLETE — RESUME FINALIZED"
- [ ] Click "EXPORT PDF": PDF downloads using finalized data
- [ ] Mobile: bottom tab bar navigates correctly between pages with no flicker
