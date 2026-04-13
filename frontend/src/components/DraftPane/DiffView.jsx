import { diffWords } from "../../utils/diffWords";

export default function DiffView({ original, current }) {
  if (!original || original === current) return null;
  const tokens = diffWords(original, current);
  const hasChanges = tokens.some((t) => t.type !== "equal");
  if (!hasChanges) return null;

  return (
    <div className="mt-2 bg-surface-container-highest px-3 py-2">
      <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1.5">
        Visual Diff
      </p>
      <p className="font-body text-sm leading-relaxed text-on-surface">
        {tokens.map((tok, i) => {
          if (tok.type === "removed")
            return (
              <span
                key={i}
                className="line-through text-error bg-error/10 px-0.5 mr-0.5"
              >
                {tok.value}
              </span>
            );
          if (tok.type === "added")
            return (
              <span
                key={i}
                className="text-primary bg-primary/10 px-0.5 mr-0.5"
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
