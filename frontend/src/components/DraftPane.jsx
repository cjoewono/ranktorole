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
          {/* key={i} is safe here because bullets are edit-in-place only (no add/remove/reorder). */}
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

      {editBullets.length === 0 && (
        <p className="text-sm text-amber-600">
          No bullets to display. Draft may be incomplete.
        </p>
      )}

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <button
        onClick={handleConfirm}
        disabled={saving || editBullets.length === 0}
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
