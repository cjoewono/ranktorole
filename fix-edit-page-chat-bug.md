# Fix: Chat not working on edit page for finalized resumes

## Context

When a user clicks "Edit & Export" on a finalized resume from the Dashboard, the app navigates to `/resume-builder?id=<uuid>&mode=edit`. The resume loads into FINALIZING phase. The user can chat in the right pane, but the message briefly shows a loading indicator then disappears — no work is done. The root cause is three interacting bugs.

## Safety check

Before doing anything, verify `backend/conftest.py` exists and contains the `autouse` fixture that globally patches `anthropic.Anthropic` with `MagicMock`.

## Bug 1: `handleChatSend` swallows 409 errors — ChatPane never locks

In `frontend/src/hooks/useResumeMachine.js`, `handleChatSend` catches ALL errors and dispatches `CHAT_FAILED`, which pops the optimistic user message and sets `state.error`. It never re-throws.

Meanwhile, `ChatPane.jsx` wraps `onSend(message)` in its own try/catch looking for `err.status === 409` to set `lockedMsg`. But since `handleChatSend` catches internally, `onSend()` never throws — ChatPane's catch block is dead code.

The result: user message appears → loading shows → backend returns 409 → `CHAT_FAILED` removes user message → loading disappears → nothing visible happens.

### Fix

In `frontend/src/hooks/useResumeMachine.js`, modify the `catch` block in `handleChatSend` to re-throw 409 errors so ChatPane can handle them:

```js
} catch (err) {
  if (err.status === 409) {
    // Don't pop the user message for 409 — let ChatPane lock the input
    // Remove the optimistic user message since it can't be processed
    dispatch({ type: "CHAT_FAILED", message: "" });
    throw err; // Re-throw so ChatPane's catch block can set lockedMsg
  }
  dispatch({ type: "CHAT_FAILED", message: err.message });
} finally {
```

Wait — `CHAT_FAILED` sets `state.error` to `action.message`. Setting it to empty string means no visible error banner, which is correct for 409 since ChatPane handles it with `lockedMsg`. But `CHAT_FAILED` also pops the last user message. That's fine for 409 — the message was rejected.

Actually, re-read the current `CHAT_FAILED` reducer:
```js
case "CHAT_FAILED":
  return {
    ...state,
    chatHistory: state.chatHistory.slice(0, -1),
    error: action.message,
  };
```

For a 409, we want to:
1. Pop the rejected user message (fine)
2. NOT set a visible error (set error to null or empty)
3. Re-throw so ChatPane locks

Apply this edit to `handleChatSend` in `frontend/src/hooks/useResumeMachine.js`. Replace the catch block:

**Current:**
```js
      } catch (err) {
        dispatch({ type: "CHAT_FAILED", message: err.message });
      } finally {
```

**New:**
```js
      } catch (err) {
        if (err.status === 409) {
          dispatch({ type: "CHAT_FAILED", message: "" });
          throw err;
        }
        dispatch({ type: "CHAT_FAILED", message: err.message });
      } finally {
```

## Bug 2: `handleConfirm` navigates to dashboard instead of showing DONE overlay

In `frontend/src/components/DraftPane/FinalizingEditor.jsx`, the `handleConfirm` function calls `navigate("/dashboard")` on success (line with `navigate("/dashboard")`). Per the spec, it should dispatch `DONE` so the split pane stays open with the export CTA.

### Fix

In `frontend/src/components/DraftPane/FinalizingEditor.jsx`:

1. Remove the `useNavigate` import and the `const navigate = useNavigate();` line.

2. Replace the success path in `handleConfirm`. Change:
```js
      await finalizeResume(resumeId, {
        civilian_title: editTitle,
        summary: editSummary,
        roles: editRoles,
      });
      navigate("/dashboard");
```
To:
```js
      await finalizeResume(resumeId, {
        civilian_title: editTitle,
        summary: editSummary,
        roles: editRoles,
      });
      dispatch({
        type: "DONE",
        draft: {
          civilian_title: editTitle,
          summary: editSummary,
          roles: editRoles,
        },
      });
```

3. Remove the `import { useNavigate } from "react-router-dom";` line at the top of the file since it's no longer used.

## Bug 3: Already-finalized resumes should lock chat on load

When entering via `?mode=edit` for a finalized resume, the chat should be locked immediately since the backend will reject all chat messages with 409.

### Fix

In `frontend/src/hooks/useResumeMachine.js`:

1. Add `isFinalized: false` to `initialState` (after `isSending: false`).

2. Add `isFinalized` to the `RESUME_LOADED` case:
```js
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
```

3. Add `isFinalized: true` to the `DONE` case. Change:
```js
    case "DONE":
      return {
        ...state,
        phase: "DONE",
        ...(action.draft ? { draft: action.draft } : {}),
      };
```
To:
```js
    case "DONE":
      return {
        ...state,
        phase: "DONE",
        isFinalized: true,
        ...(action.draft ? { draft: action.draft } : {}),
      };
```

4. In the `useEffect` that loads from DB, pass `isFinalized` from the API response:
```js
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
          isFinalized: resume.is_finalized || false,
        });
```

5. In `frontend/src/pages/ResumeBuilder.jsx`, pass `isFinalized` to ChatPane. Find where `<ChatPane` is rendered and add the prop. The ChatPane already receives `phase` — also add:
```jsx
            <ChatPane
              chatHistory={state.chatHistory}
              resumeId={state.resumeId}
              phase={state.phase}
              dispatch={dispatch}
              onSend={handleChatSend}
              isSending={state.isSending}
              isFinalized={state.isFinalized}
            />
```

6. In `frontend/src/components/ChatPane.jsx`:

Update the component signature to accept `isFinalized`:
```jsx
export default function ChatPane({
  chatHistory = [],
  resumeId,
  phase,
  dispatch,
  onSend,
  isSending = false,
  isFinalized = false,
}) {
```

Update the `isLocked` calculation to include `isFinalized`:
```js
const isLocked = phase === "DONE" || isFinalized || lockedMsg !== null;
```

Update the locked message display. Find the `isLocked` conditional render block:
```jsx
      ) : isLocked ? (
        <div className="border-t border-outline-variant/20 px-4 py-3 font-label text-xs tracking-widest uppercase text-on-surface-variant">
          MISSION COMPLETE — RESUME FINALIZED
        </div>
      ) : (
```

Change the message to handle both cases:
```jsx
      ) : isLocked ? (
        <div className="border-t border-outline-variant/20 px-4 py-3 font-label text-xs tracking-widest uppercase text-on-surface-variant">
          {phase === "DONE"
            ? "MISSION COMPLETE — RESUME FINALIZED"
            : "CHAT LOCKED — RESUME ALREADY FINALIZED"}
        </div>
      ) : (
```

## Verification

1. `npm run build` — should pass with no errors
2. `pytest --tb=short -q` — all 116 tests should still pass (no backend changes)
3. Manual smoke test:
   - Create a new resume, generate draft, chat, finalize via Confirm Final → should show DONE overlay with Export PDF + Back to Dashboard (NOT navigate away)
   - From dashboard, click "Edit & Export" on a finalized resume → chat pane should show "CHAT LOCKED — RESUME ALREADY FINALIZED" immediately, no input field
   - Editing bullets in the FinalizingEditor should still work (local state only)
   - The "Confirm Final" button will return 409 for already-finalized resumes — that error is already handled by the catch block in `handleConfirm` and will show in the error banner

## Files modified

- `frontend/src/hooks/useResumeMachine.js` — add `isFinalized` to state, pass through `RESUME_LOADED`/`DONE`, re-throw 409 in `handleChatSend`
- `frontend/src/components/DraftPane/FinalizingEditor.jsx` — dispatch DONE instead of navigate("/dashboard"), remove useNavigate
- `frontend/src/components/ChatPane.jsx` — accept `isFinalized` prop, lock input when true
- `frontend/src/pages/ResumeBuilder.jsx` — pass `state.isFinalized` to ChatPane
