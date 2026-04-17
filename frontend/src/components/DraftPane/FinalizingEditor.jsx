import { useState, useEffect } from "react";
import { finalizeResume } from "../../api/resumes";
import BulletEditor from "./BulletEditor";

export default function FinalizingEditor({
  draft,
  aiInitialDraft,
  aiSuggestions,
  bulletFlags,
  summaryFlags = [],
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
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [verifiedFlags, setVerifiedFlags] = useState(new Set());

  function getFlagsFor(roleIdx, bulletIdx) {
    const entry = (bulletFlags || []).find(
      (f) => f.role_index === roleIdx && f.bullet_index === bulletIdx,
    );
    return entry ? entry.flags : [];
  }

  function toggleVerified(roleIdx, bulletIdx) {
    const key = `${roleIdx}-${bulletIdx}`;
    setVerifiedFlags((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function isVerified(roleIdx, bulletIdx) {
    return verifiedFlags.has(`${roleIdx}-${bulletIdx}`);
  }

  const SUMMARY_KEY = "__summary__";

  function toggleSummaryVerified() {
    setVerifiedFlags((prev) => {
      const next = new Set(prev);
      if (next.has(SUMMARY_KEY)) next.delete(SUMMARY_KEY);
      else next.add(SUMMARY_KEY);
      return next;
    });
  }

  function hasFlags(roleIdx, bulletIdx) {
    return getFlagsFor(roleIdx, bulletIdx).length > 0;
  }

  // Auto-apply AI chat suggestions to the editable state when they arrive
  useEffect(() => {
    if (!aiSuggestions || aiSuggestions.length === 0) return;
    setEditRoles(
      aiSuggestions.map((role) => ({ ...role, bullets: [...role.bullets] })),
    );
    dispatch({ type: "AI_SUGGESTIONS_CLEARED" });
  }, [aiSuggestions]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleToggle(roleIdx, bulletIdx) {
    const key = `${roleIdx}-${bulletIdx}`;
    setExpandedKey((prev) => (prev === key ? null : key));
  }

  function handleAcceptSuggestion(roleIdx, bulletIdx, val) {
    handleBulletChange(roleIdx, bulletIdx, val);
    // verification cleared inside handleBulletChange
  }

  function handleDismissSuggestion(roleIdx, bulletIdx) {
    setVerifiedFlags((prev) => {
      const next = new Set(prev);
      next.delete(`${roleIdx}-${bulletIdx}`);
      return next;
    });
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
    // If bullet was verified, clear it — edited bullets must be re-verified
    setVerifiedFlags((prev) => {
      const next = new Set(prev);
      next.delete(`${roleIdx}-${bulletIdx}`);
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
      dispatch({
        type: "DONE",
        draft: {
          civilian_title: editTitle,
          summary: editSummary,
          roles: editRoles,
        },
      });
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

  const flaggedBullets = (editRoles || []).flatMap((role, roleIdx) =>
    (role.bullets || [])
      .map((_, bulletIdx) => ({ roleIdx, bulletIdx }))
      .filter(({ roleIdx: r, bulletIdx: b }) => hasFlags(r, b)),
  );

  const summaryIsFlagged = (summaryFlags || []).length > 0;
  const summaryVerified = verifiedFlags.has(SUMMARY_KEY);

  const totalFlagged = flaggedBullets.length + (summaryIsFlagged ? 1 : 0);
  const verifiedCount =
    flaggedBullets.filter(({ roleIdx, bulletIdx }) =>
      isVerified(roleIdx, bulletIdx),
    ).length + (summaryIsFlagged && summaryVerified ? 1 : 0);
  const allFlagsResolved = totalFlagged === 0 || verifiedCount === totalFlagged;

  return (
    <div className="flex flex-col h-full">
      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Header */}
        <h2 className="font-headline font-bold text-xl uppercase text-on-surface tracking-wide">
          Edit &amp; Finalize
        </h2>

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
            onChange={(e) => {
              setEditSummary(e.target.value);
              setVerifiedFlags((prev) => {
                const next = new Set(prev);
                next.delete(SUMMARY_KEY);
                return next;
              });
            }}
            className="tactical-input resize-y"
          />
          {summaryIsFlagged && (
            <>
              <div className="bg-surface-container px-3 py-2 space-y-1 border-l-2 border-amber-400 mt-2">
                <p className="font-label text-xs tracking-widest uppercase text-amber-400 mb-1">
                  Grounding Check — Summary
                </p>
                <ul className="space-y-1">
                  {summaryFlags.map((flag, i) => (
                    <li
                      key={i}
                      className="font-body text-xs text-on-surface-variant leading-relaxed"
                    >
                      • {flag}
                    </li>
                  ))}
                </ul>
              </div>
              <label className="flex items-start gap-2 pt-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={summaryVerified}
                  onChange={toggleSummaryVerified}
                  className="mt-0.5 shrink-0 accent-secondary"
                />
                <span className="font-body text-xs text-on-surface leading-relaxed">
                  I verified the summary's claims against my actual experience.
                </span>
              </label>
            </>
          )}
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
                {(role.bullets || []).map((bullet, bulletIdx) => (
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
                    suggestion={aiSuggestions?.[roleIdx]?.bullets?.[bulletIdx]}
                    onAccept={(s) =>
                      handleAcceptSuggestion(roleIdx, bulletIdx, s)
                    }
                    onDismiss={() =>
                      handleDismissSuggestion(roleIdx, bulletIdx)
                    }
                    flags={getFlagsFor(roleIdx, bulletIdx)}
                    verified={isVerified(roleIdx, bulletIdx)}
                    onToggleVerified={() => toggleVerified(roleIdx, bulletIdx)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>

        {error && (
          <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3">
            {error}
          </div>
        )}
      </div>

      {/* Pinned footer — never scrolls */}
      <div className="border-t border-outline-variant/20 bg-surface-container-low p-4">
        {totalFlagged > 0 && (
          <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant text-center pb-2">
            {verifiedCount} of {totalFlagged} flagged{" "}
            {totalFlagged === 1 ? "item" : "items"} verified
          </p>
        )}
        {totalFlagged === 0 && (
          <p className="font-label text-xs tracking-widest uppercase text-secondary text-center pb-2">
            ✓ All claims passed grounding checks
          </p>
        )}
        <button
          type="button"
          onClick={handleConfirm}
          disabled={saving || editRoles.length === 0 || !allFlagsResolved}
          className="mission-gradient w-full text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md disabled:opacity-50 transition-opacity"
        >
          {saving ? "SAVING..." : "CONFIRM FINAL"}
        </button>
      </div>
    </div>
  );
}
