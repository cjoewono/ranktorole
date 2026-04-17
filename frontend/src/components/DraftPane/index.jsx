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
  bulletFlags,
  summaryFlags,
  phase,
  dispatch,
  resumeId,
}) {
  if (!draft) return null;

  // DONE — export CTA only appears after finalization
  if (phase === "DONE") {
    return (
      <div className="bg-surface-container-low p-5 flex flex-col items-center justify-center flex-1 space-y-6 text-center">
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
                roles: draft.roles ?? [],
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
      <div className="bg-surface-container-low flex flex-col flex-1 overflow-hidden">
        <FinalizingEditor
          draft={draft}
          aiInitialDraft={aiInitialDraft}
          aiSuggestions={aiSuggestions}
          bulletFlags={bulletFlags}
          summaryFlags={summaryFlags}
          resumeId={resumeId}
          dispatch={dispatch}
        />
      </div>
    );
  }

  // REVIEWING phase — read-only role cards
  if (!draft.roles) return null;
  return (
    <div className="bg-surface-container-low p-5 space-y-5 overflow-y-auto flex-1">
      {/* Title + summary */}
      <div>
        <h2 className="font-headline font-bold text-2xl uppercase text-on-surface">
          {draft.civilian_title}
        </h2>
        <p className="font-body text-sm text-on-surface-variant leading-relaxed mt-2">
          {draft.summary}
        </p>
      </div>

      {/* Role cards */}
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
