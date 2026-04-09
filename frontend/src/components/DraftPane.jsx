import { useState } from "react";
import jsPDF from "jspdf";
import { finalizeResume } from "../api/resumes";
import { diffWords } from "../utils/diffWords";

// ── PDF export ───────────────────────────────────────────────────────────────

function exportPDF({ civilian_title, summary, roles }) {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const marginL = 20,
    marginR = 20,
    marginT = 20;
  const pageW = 210,
    contentW = pageW - marginL - marginR; // 170mm
  let y = marginT;

  const checkPage = () => {
    if (y > 270) {
      doc.addPage();
      y = marginT;
    }
  };

  // Title
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text(civilian_title || "Resume", marginL, y);
  y += 8;
  doc.setDrawColor(200, 200, 200);
  doc.line(marginL, y, pageW - marginR, y);

  // Summary label
  y += 10;
  checkPage();
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text("Summary", marginL, y);

  // Summary text
  y += 5;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  const summaryLines = doc.splitTextToSize(summary || "", contentW);
  summaryLines.forEach((line) => {
    checkPage();
    doc.text(line, marginL, y);
    y += 5;
  });
  y += 6;

  // Roles
  (roles || []).forEach((role) => {
    // Role title
    y += 10;
    checkPage();
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text(role.title || "", marginL, y);

    // Org · Dates
    y += 6;
    checkPage();
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(100, 100, 100);
    const orgDates = [role.org, role.dates].filter(Boolean).join(" · ");
    doc.text(orgDates, marginL, y);
    doc.setTextColor(0, 0, 0);

    // Bullets
    doc.setFontSize(10);
    (role.bullets || []).forEach((bullet) => {
      const lines = doc.splitTextToSize(`• ${bullet}`, contentW - 6);
      lines.forEach((line) => {
        y += 5;
        checkPage();
        doc.text(line, marginL + 6, y);
      });
      y += 3;
    });
    y += 6;
  });

  const filename =
    (civilian_title || "resume").replace(/\s+/g, "_") + "_resume.pdf";
  doc.save(filename);
}

// ── Inline diff renderer ─────────────────────────────────────────────────────

function DiffView({ original, current }) {
  if (!original || original === current) return null;
  const tokens = diffWords(original, current);
  const hasChanges = tokens.some((t) => t.type !== "equal");
  if (!hasChanges) return null;

  return (
    <div className="mt-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
      <p className="text-xs font-medium text-gray-400 mb-1.5">Visual Diff</p>
      <p className="text-sm leading-relaxed">
        {tokens.map((tok, i) => {
          if (tok.type === "removed")
            return (
              <span
                key={i}
                className="line-through text-red-500 bg-red-50 rounded px-0.5 mr-0.5"
              >
                {tok.value}
              </span>
            );
          if (tok.type === "added")
            return (
              <span
                key={i}
                className="text-amber-600 bg-amber-50 rounded px-0.5 mr-0.5"
              >
                {tok.value}
              </span>
            );
          return (
            <span key={i} className="mr-0.5">
              {tok.value}
            </span>
          );
        })}
      </p>
    </div>
  );
}

// ── Accordion bullet editor ──────────────────────────────────────────────────

function BulletEditor({
  value,
  original,
  expanded,
  onToggle,
  onChange,
  suggestion,
  onAccept,
  onDismiss,
}) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header row — click to expand/collapse */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-start gap-2 px-3 py-2.5 text-left hover:bg-gray-50 transition-colors"
      >
        <span className="text-gray-400 shrink-0 mt-0.5">•</span>
        <span className="flex-1 text-sm text-gray-800 leading-relaxed">
          {value}
        </span>
        <span className="text-gray-400 text-xs shrink-0 mt-0.5">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {/* Expanded editor */}
      {expanded && (
        <div className="border-t border-gray-200 px-3 py-3 bg-blue-50 space-y-2">
          <textarea
            rows={4}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y bg-white"
          />
          <DiffView original={original} current={value} />

          {/* AI suggestion chip */}
          {suggestion && suggestion !== value && (
            <div className="rounded-lg bg-gray-100 px-3 py-2 space-y-1.5">
              <p className="text-xs text-gray-500 mb-1">
                AI suggested revision
              </p>
              <p className="text-sm text-gray-700 italic">{suggestion}</p>
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => onAccept(suggestion)}
                  className="text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded-md transition-colors"
                >
                  Accept
                </button>
                <button
                  type="button"
                  onClick={onDismiss}
                  className="text-xs font-semibold text-gray-600 hover:text-gray-800 px-3 py-1 rounded-md border border-gray-300 hover:bg-gray-50 transition-colors"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Finalizing editor ────────────────────────────────────────────────────────

function FinalizingEditor({
  draft,
  aiInitialDraft,
  aiSuggestions,
  resumeId,
  dispatch,
}) {
  if (!draft || !draft.roles) return null;
  const [editTitle, setEditTitle] = useState(draft.civilian_title);
  const [editSummary, setEditSummary] = useState(draft.summary);
  // Deep copy so edits don't mutate reducer state
  const [editRoles, setEditRoles] = useState(() =>
    (draft.roles || []).map((role) => ({
      ...role,
      bullets: [...role.bullets],
    })),
  );
  // expandedKey: "roleIdx-bulletIdx" or null — only one bullet open at a time globally
  const [expandedKey, setExpandedKey] = useState(null);
  // Track dismissed AI suggestion chips by "roleIdx-bulletIdx" key
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
    setEditRoles((prev) => {
      const next = prev.map((role, ri) => {
        if (ri !== roleIdx) return role;
        const bullets = [...role.bullets];
        bullets[bulletIdx] = val;
        return { ...role, bullets };
      });
      return next;
    });
  }

  // Returns the AI-suggested bullet text for a given position, or null
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
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Header row: Return to Chat (left) + Export PDF (right) */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => dispatch({ type: "RETURN_TO_CHAT" })}
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
        >
          ← Return to Chat
        </button>
        <button
          type="button"
          onClick={() =>
            exportPDF({
              civilian_title: editTitle,
              summary: editSummary,
              roles: editRoles,
            })
          }
          className="border border-blue-600 text-blue-600 hover:bg-blue-50 text-sm font-semibold px-4 py-1.5 rounded-lg transition-colors"
        >
          Export PDF
        </button>
      </div>

      <h2 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">
        Edit &amp; Finalize
      </h2>

      {/* Title */}
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

      {/* Summary */}
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">
          Summary
        </label>
        <textarea
          rows={5}
          value={editSummary}
          onChange={(e) => setEditSummary(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
        />
      </div>

      {/* Roles — accordion bullets per role */}
      <div className="space-y-4">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          Roles
        </p>
        {(editRoles || []).map((role, roleIdx) => (
          <div
            key={roleIdx}
            className="border border-gray-200 rounded-xl p-4 space-y-2"
          >
            {/* Role header (read-only) */}
            <p className="font-semibold text-gray-900 text-sm">{role.title}</p>
            <p className="text-xs text-gray-500">
              {role.org}
              {role.org && role.dates ? " · " : ""}
              {role.dates}
            </p>

            {/* Bullet accordion */}
            <div className="space-y-2 mt-2">
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

      {error && <p className="text-red-600 text-sm">{error}</p>}

      {/* Sticky confirm button */}
      <div className="sticky bottom-0 bg-white pt-2 pb-4">
        <button
          type="button"
          onClick={handleConfirm}
          disabled={saving || editRoles.length === 0}
          className="w-full bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition-colors"
        >
          {saving ? "Saving..." : "Confirm Final"}
        </button>
      </div>
    </div>
  );
}

// ── DraftPane (public) ───────────────────────────────────────────────────────

export default function DraftPane({
  draft,
  aiInitialDraft,
  aiSuggestions,
  phase,
  dispatch,
  resumeId,
}) {
  if (!draft) return null;

  if (phase === "FINALIZING") {
    if (!draft || !draft.roles) return null;
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
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
  if (!draft || !draft.roles) return null;
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
      <h2 className="font-semibold text-gray-900 text-xl">
        {draft.civilian_title}
      </h2>

      <p className="text-sm text-gray-700 leading-relaxed">{draft.summary}</p>

      {(draft.roles || []).map((role, roleIdx) => (
        <div
          key={roleIdx}
          className="border border-gray-200 rounded-xl p-4 space-y-2 mb-6 shadow-sm"
        >
          <p className="font-semibold text-base text-gray-900">{role.title}</p>
          <p className="text-sm text-gray-500">
            {role.org}
            {role.org && role.dates ? " · " : ""}
            {role.dates}
          </p>
          <ul className="space-y-1 mt-1">
            {(role.bullets || []).map((b, bi) => (
              <li key={bi} className="flex gap-2 pl-4">
                <span className="text-gray-400 shrink-0">•</span>
                <span className="text-sm text-gray-800 leading-relaxed">
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
        className="bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
      >
        Approve &amp; Edit
      </button>
    </div>
  );
}
