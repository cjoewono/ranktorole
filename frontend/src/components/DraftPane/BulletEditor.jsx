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
  flags = [],
  verified = false,
  onToggleVerified,
}) {
  return (
    <div className="bg-surface-container overflow-hidden">
      {/* Header row */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-start gap-2 px-3 py-2.5 text-left hover:bg-surface-container-high transition-colors"
      >
        <span
          className={`shrink-0 mt-0.5 ${
            flags.length === 0
              ? "text-on-surface-variant"
              : verified
                ? "text-secondary"
                : "text-amber-400"
          }`}
        >
          {flags.length === 0 ? "•" : verified ? "✓" : "•"}
        </span>
        <span className="flex-1 font-body text-sm text-on-surface leading-relaxed">
          {value}
        </span>
        {flags.length > 0 && (
          <span
            className="shrink-0 text-amber-400 text-xs font-label tracking-widest uppercase mr-2"
            title={flags.join(" • ")}
            aria-label={`${flags.length} grounding ${flags.length === 1 ? "flag" : "flags"}`}
          >
            ⚠ {flags.length}
          </span>
        )}
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

          {/* Grounding flag details */}
          {flags.length > 0 && (
            <div className="bg-surface-container px-3 py-2 space-y-1 border-l-2 border-amber-400">
              <p className="font-label text-xs tracking-widest uppercase text-amber-400 mb-1">
                Grounding Check
              </p>
              <ul className="space-y-1">
                {flags.map((flag, i) => (
                  <li
                    key={i}
                    className="font-body text-xs text-on-surface-variant leading-relaxed"
                  >
                    • {flag}
                  </li>
                ))}
              </ul>
            </div>
          )}

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

          {/* Honesty confirmation — only for flagged bullets */}
          {flags.length > 0 && (
            <label className="flex items-start gap-2 pt-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={verified}
                onChange={onToggleVerified}
                className="mt-0.5 shrink-0 accent-secondary"
              />
              <span className="font-body text-xs text-on-surface leading-relaxed">
                I verified this bullet&apos;s claims against my actual
                experience.
              </span>
            </label>
          )}
        </div>
      )}
    </div>
  );
}
