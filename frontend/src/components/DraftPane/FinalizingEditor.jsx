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
            {/* Role header */}
            <p className="font-headline font-semibold text-on-surface uppercase text-sm">
              {role.title}
            </p>
            <p className="font-label text-xs tracking-widest uppercase text-outline">
              {role.org}
              {role.org && role.dates ? " · " : ""}
              {role.dates}
            </p>

            {/* Bullet accordion */}
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
