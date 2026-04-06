export default function ResumeOutput({ result }) {
  if (!result) return null;

  const { civilian_title, summary, bullets, created_at } = result;

  return (
    <div className="mt-8 rounded-xl border border-blue-100 bg-blue-50 p-6 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-xl font-bold text-blue-900">{civilian_title}</h2>
        {created_at && (
          <span className="text-xs text-gray-400 whitespace-nowrap mt-1">
            {new Date(created_at).toLocaleDateString()}
          </span>
        )}
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-blue-600 mb-1">
          Summary
        </h3>
        <p className="text-sm text-gray-700 leading-relaxed">{summary}</p>
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-blue-600 mb-2">
          Resume Bullets
        </h3>
        <ul className="space-y-1.5">
          {bullets.map((bullet, i) => (
            <li key={i} className="flex gap-2 text-sm text-gray-700">
              <span className="text-blue-400 mt-0.5 shrink-0">&#8226;</span>
              <span>{bullet}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
