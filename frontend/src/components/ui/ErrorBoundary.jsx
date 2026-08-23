/**
 * React Error Boundary
 * ====================
 * Catches unhandled JavaScript rendering errors in subtrees and provides
 * a clean recovery interface instead of blanking out the whole page.
 */

import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 my-6 bg-red-950/40 border border-red-500/30 rounded-3xl text-center space-y-4 max-w-lg mx-auto backdrop-blur-xl">
          <div className="w-12 h-12 rounded-2xl bg-red-500/10 text-red-400 flex items-center justify-center mx-auto text-xl font-bold border border-red-500/20">
            ⚠️
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Component Encountered an Issue</h3>
            <p className="text-xs text-gray-400 mt-1">
              {this.state.error?.message || "An unexpected rendering error occurred in this view."}
            </p>
          </div>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-red-600 hover:bg-red-500 transition-all shadow-lg shadow-red-600/20"
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
