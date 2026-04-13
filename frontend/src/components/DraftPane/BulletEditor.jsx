import DiffView from "./DiffView";

export default function BulletEditor({
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
    <div className="bg-surface-container overflow-hidden">
      {/* Header row */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-start gap-2 px-3 py-2.5 text-left hover:bg-surface-container-high transition-colors"
      >
        <span className="text-secondary shrink-0 mt-0.5">•</span>
        <span className="flex-1 font-body text-sm text-on-surface leading-relaxed">
          {value}
        </span>
        <span className="text-on-surface-variant text-xs shrink-0 mt-0.5">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {/* Expanded editor */}
      {expanded && (
        <div className="px-3 py-3 bg-surface-container-highest space-y-2">
          <textarea
            rows={4}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="tactical-input resize-y"
          />
          <DiffView original={original} current={value} />

          {/* AI suggestion chip */}
          {suggestion && suggestion !== value && (
            <div className="bg-surface-container px-3 py-2 space-y-1.5">
              <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                AI Suggested Revision
              </p>
              <p className="font-body text-sm text-on-surface italic">
                {suggestion}
              </p>
              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => onAccept(suggestion)}
                  className="font-label text-xs tracking-widest uppercase text-secondary hover:opacity-80 transition-opacity"
                >
                  Accept
                </button>
                <button
                  type="button"
                  onClick={onDismiss}
                  className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-on-surface transition-colors"
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
