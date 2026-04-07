export default function SplitPane({ left, right }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-0 md:divide-x md:divide-gray-200">
      <div className="min-w-0 p-4 md:pr-6">{left}</div>
      <div className="min-w-0 p-4 md:pl-6">{right}</div>
    </div>
  );
}
