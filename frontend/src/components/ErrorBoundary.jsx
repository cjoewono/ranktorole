import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-background flex items-center justify-center p-8">
          <div className="bg-surface-container-low p-8 max-w-md text-center space-y-4">
            <div className="flex items-center justify-center gap-2">
              <span className="w-2 h-2 rounded-full bg-error inline-block" />
              <span className="font-label text-xs tracking-widest uppercase text-error">
                SYSTEM ERROR
              </span>
            </div>
            <h1 className="font-headline font-bold text-2xl uppercase text-on-surface">
              Something went wrong
            </h1>
            <p className="font-body text-sm text-on-surface-variant">
              An unexpected error occurred. Try refreshing the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-sm px-6 py-2.5 rounded-md"
            >
              RELOAD
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
