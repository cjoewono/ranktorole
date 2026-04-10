export default function ResumeOutput({ result }) {
  if (!result) return null;

  const { civilian_title, summary, roles, created_at } = result;

  return (
    <div className="mt-8 rounded-xl border border-slate-200 bg-white shadow-sm p-6 space-y-5">
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-xl font-bold text-slate-900">{civilian_title}</h2>
        {created_at && (
          <span className="text-xs text-slate-400 whitespace-nowrap mt-1">
            {new Date(created_at).toLocaleDateString()}
          </span>
        )}
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-blue-500 mb-1">
          Summary
        </h3>
        <p className="text-sm text-slate-700 leading-relaxed">{summary}</p>
      </div>

      {(roles || []).map((role, ri) => (
        <div key={ri}>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-blue-500 mb-1">
            Experience
          </h3>
          <div className="mb-2">
            <p className="font-semibold text-slate-800 text-sm">{role.title}</p>
            <p className="text-xs text-slate-500">
              {role.org} · {role.dates}
            </p>
          </div>
          <ul className="space-y-1.5">
            {(role.bullets || []).map((bullet, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-700">
                <span className="text-blue-500 mt-0.5 shrink-0">&#8226;</span>
                <span>{bullet}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
