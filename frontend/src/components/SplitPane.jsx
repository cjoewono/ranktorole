// SplitPane — flex layout with sticky right pane (chat)
// Container height = 100vh minus NavBar (~64px); overflow hidden prevents scroll bleed
export default function SplitPane({ left, right }) {
  return (
    <div
      className="flex flex-row border-t border-outline-variant/20"
      style={{ height: "calc(100vh - 64px)", overflow: "hidden" }}
    >
      {/* Left pane — overflow-hidden; each child manages its own scroll */}
      <div className="flex-1 min-w-0 overflow-hidden bg-background flex flex-col">
        {left}
      </div>

      {/* Right pane — sticky chat, fixed width, independently scrollable */}
      <div
        className="w-[420px] flex-shrink-0 border-l border-outline-variant/20 bg-surface-container-low overflow-y-auto"
        style={{ height: "100%" }}
      >
        {right}
      </div>
    </div>
  );
}
