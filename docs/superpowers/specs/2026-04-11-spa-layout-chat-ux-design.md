# SPA Layout, Chat UX & Finalize/Export Flow

**Date:** 2026-04-11
**Status:** Approved

---

## Problem Statement

The current frontend has three issues:

1. **Page flicker and state loss** — every page owns its own `<NavBar>` and `min-h-screen` wrapper, so navigating between routes remounts everything. Form state, scroll position, and in-progress work are lost on navigation.
2. **Chat has no loading feedback** — users cannot tell whether a chat message is being processed, causing repeated submissions and confusion.
3. **Confirm Final / Export UX is ambiguous** — Export is available before the resume is saved, and after confirmation the split pane disappears along with the draft.

---

## Approach

Always-mounted pages behind a persistent shell. All three protected pages render simultaneously; inactive ones are hidden with `display: none`. The shell owns the NavBar and never unmounts. Chat gets explicit `isSending` state. The finalize/export sequence is reordered to be unambiguous.

---

## Section 1 — Shell Architecture & State Preservation

### AppShell

`App.jsx` gains an `AppShell` component that:

- Renders `<NavBar>` once at the top level — it never remounts.
- Renders all three protected pages simultaneously, wrapped in visibility containers.
- Reads `location.pathname` via `useLocation()` to decide which container is visible.
- Inactive containers receive `className="hidden"` (`display: none`) — components stay mounted, state is fully preserved.

```
AppShell
├── <NavBar />
├── <div hidden={route !== '/dashboard'}>    <Dashboard />    </div>
├── <div hidden={route !== '/contacts'}>     <Contacts />     </div>
└── <div hidden={route !== '/resume-builder'}> <ResumeBuilder /> </div>
```

React Router links update the URL as normal. Login and Register remain outside the shell with their own auth layout. Each page container wraps its page component in its own `<Suspense>` boundary so lazy-loaded pages load independently without blocking each other.

### Page component cleanup

Each page component removes:

- Its own `<NavBar>` import and render
- Its outer `min-h-screen bg-background pb-20 md:pb-0` wrapper

The shell provides these structurally.

### ResumeBuilder full-screen mode

AppShell holds a `fullscreen` boolean in local state and passes a `setFullscreen` setter down to ResumeBuilder as a prop. ResumeBuilder calls it via `useEffect` whenever phase enters or exits `REVIEWING`/`FINALIZING`. AppShell reads `fullscreen` to switch into `data-layout="fullscreen"` mode — removing `max-width` and content padding constraints so the split pane fills the entire viewport.

Two shell content modes:

- **`normal`** — `max-w-4xl mx-auto px-4` (or `max-w-2xl` for builder init view)
- **`fullscreen`** — zero padding, `flex-fill`, used exclusively by the split pane

---

## Section 2 — Uniform Page Layout

### PageHeader component

The repeated header pattern (status chip + big headline + optional action button) is extracted into a single `PageHeader` component:

```jsx
<PageHeader
  label="SYSTEM ACTIVE / CORE_OPERATIONS"
  title={
    <>
      YOUR
      <br />
      DEPLOYMENTS
    </>
  }
  action={<button>+ NEW RESUME</button>} // optional
/>
```

Used by: Dashboard, Contacts, ResumeBuilder upload/init view.

### Structural classes

`AppShell` owns `min-h-screen bg-background pb-20 md:pb-0`. Pages no longer declare screen-level wrappers — their JSX starts at content.

### Max-width containers (standardized)

| View                      | Container                     |
| ------------------------- | ----------------------------- |
| Dashboard                 | `max-w-4xl mx-auto px-4 py-6` |
| Contacts                  | `max-w-4xl mx-auto px-4 py-6` |
| ResumeBuilder upload/init | `max-w-2xl mx-auto px-4 py-8` |
| ResumeBuilder split pane  | Full viewport, no container   |

---

## Section 3 — Chat Loading Indicator

### State change

`useResumeMachine` adds `isSending: false` to its initial state. The `handleChatSend` function sets `isSending: true` before the API call and back to `false` in the `finally` block (covers both success and error).

### ChatPane changes

`ChatPane` receives `isSending` as a prop. While `isSending` is `true`:

1. A **thinking bubble** appears at the bottom of the message list — styled as an assistant message with three pulsing dots and the label `PROCESSING REQUEST...`
2. The **chat input is disabled**
3. The **send button** is disabled and its label changes from `SEND` to `SENDING...`

This gives three simultaneous signals so there is no ambiguity about whether the request registered. Error handling is unchanged — errors from the machine's `error` state surface as before.

---

## Section 4 — Confirm Final & Export Flow

### Current problems

- "Export PDF" button is present in the FINALIZING view header before the resume is saved.
- After "Confirm Final", the split pane disappears and the export opportunity is gone.
- The sequence (edit → save → export) is not visually enforced.

### New flow

**Step 1 — REVIEWING:** User reviews the AI draft. Clicks "Approve & Edit" → enters FINALIZING.

**Step 2 — FINALIZING:** User edits bullets, title, summary. The "Export PDF" button is **removed** from this view. The only primary action is "Confirm Final".

**Step 3 — Confirm Final:** Fires `PATCH /api/v1/resumes/{id}/finalize/`. On success, the split pane stays open. The DraftPane transitions to a **DONE overlay** rendered inside the left pane:

```
┌──────────────────────────────────┐
│  ● MISSION COMPLETE              │
│                                  │
│  [      EXPORT PDF       ]       │  ← primary CTA, full-width gradient
│  [  Back to Dashboard    ]       │  ← secondary, text link
└──────────────────────────────────┘
```

**Step 4 — Export:** Uses finalized data already in local state — no additional API call. Triggers the existing `exportPDF` utility.

**Chat pane after finalization:** Input is locked with a `MISSION COMPLETE — RESUME FINALIZED` label. The chat history remains visible for reference.

### Enforced sequence

```
REVIEWING → FINALIZING → [Confirm Final] → DONE overlay → Export PDF
```

Export only appears after the data is saved. There is no way to export an unsaved draft.

---

## Files Changed

| File                                                     | Change                                               |
| -------------------------------------------------------- | ---------------------------------------------------- |
| `frontend/src/App.jsx`                                   | Add AppShell with always-mounted pages               |
| `frontend/src/components/NavBar.jsx`                     | No changes                                           |
| `frontend/src/components/PageHeader.jsx`                 | New component                                        |
| `frontend/src/pages/Dashboard.jsx`                       | Remove NavBar, outer wrapper, use PageHeader         |
| `frontend/src/pages/Contacts.jsx`                        | Remove NavBar, outer wrapper, use PageHeader         |
| `frontend/src/pages/ResumeBuilder.jsx`                   | Remove NavBar, outer wrapper, signal fullscreen mode |
| `frontend/src/hooks/useResumeMachine.js`                 | Add `isSending` state                                |
| `frontend/src/components/ChatPane.jsx`                   | Add thinking bubble, disable input while sending     |
| `frontend/src/components/DraftPane/FinalizingEditor.jsx` | Remove Export button, add DONE overlay               |

---

## Out of Scope

- Backend changes (none required)
- CSS animations beyond existing pulse utility
- Lazy loading changes (lazy imports remain, but pages stay mounted after first load)
- Login/Register pages (separate auth layout, unaffected)
