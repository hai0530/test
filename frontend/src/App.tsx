import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { queryClient } from "@/lib/queryClient";
import { AppRouter } from "@/router";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <AppRouter />
      </ErrorBoundary>
      <Toaster position="top-right" />
    </QueryClientProvider>
  );
}

export default App;
