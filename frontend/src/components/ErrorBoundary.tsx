import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Keep the error boundary safe for production; a logger can consume this later.
    console.error("Unhandled frontend error", { error, componentStack: info.componentStack });
  }

  private recover = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <main className="min-h-screen grid place-items-center bg-muted/40 p-6">
        <section className="w-full max-w-md rounded-lg border bg-card p-6 text-center shadow-sm" role="alert">
          <h1 className="text-lg font-semibold">Something went wrong</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            The application could not render this page. Reload to try again.
          </p>
          <button
            type="button"
            className="mt-5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={this.recover}
          >
            Reload
          </button>
        </section>
      </main>
    );
  }
}
