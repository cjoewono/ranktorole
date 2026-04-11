export default function PageHeader({ label, title, action }) {
  return (
    <div className="bg-surface-container-low px-4 pt-4 pb-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
        <span className="font-label text-xs tracking-widest uppercase text-secondary">
          {label}
        </span>
      </div>
      <div className="flex items-start justify-between gap-4">
        <h1 className="font-headline font-bold text-4xl uppercase text-on-surface leading-tight">
          {title}
        </h1>
        {action && <div className="shrink-0 mt-1">{action}</div>}
      </div>
    </div>
  );
}
