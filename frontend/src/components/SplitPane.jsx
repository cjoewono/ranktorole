// SplitPane — flex layout with sticky right pane (chat)
// Container height = 100vh minus NavBar (~64px); overflow hidden prevents scroll bleed
export default function SplitPane({ left, right }) {
  return (
    <div
      className="flex flex-row border-t border-gray-200"
      style={{ height: "calc(100vh - 64px)", overflow: "hidden" }}
    >
      {/* Left pane — scrollable draft content */}
      <div className="flex-1 min-w-0 overflow-y-auto p-6">{left}</div>

      {/* Right pane — sticky chat, fixed width, independently scrollable */}
      <div
        className="w-[420px] flex-shrink-0 border-l border-gray-200 bg-white overflow-y-auto"
        style={{ height: "100%" }}
      >
        {right}
      </div>
    </div>
  );
}
