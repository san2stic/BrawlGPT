/**
 * Error Boundary component for catching React errors
 */

import React, { Component, ErrorInfo } from "react";
import type { ErrorBoundaryProps, ErrorBoundaryState } from "../types";

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to console in development
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-slate-800 rounded-2xl p-8 text-center border border-red-500/30 shadow-[0_0_30px_rgba(239,68,68,0.15)]">
            <div className="text-6xl mb-4">💥</div>
            <h2 className="text-2xl font-black text-white mb-4">
              Oops! Something went wrong
            </h2>
            <p className="text-slate-400 mb-6">
              {this.state.error?.message || "An unexpected error occurred"}
            </p>
            <button
              onClick={this.handleRetry}
              className="w-full bg-gradient-to-r from-red-500 to-orange-600 text-white font-bold py-3 rounded-xl shadow-lg hover:scale-[1.02] active:scale-95 transition-transform uppercase tracking-wider"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
