import { useState } from "react";
import { ChevronLeft, ChevronRight, LogOut, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { useTags } from "../api/tags";
import { useTodos, type TodoFilters } from "../api/todos";
import { TodoFilters as TodoFiltersBar } from "./TodoFilters";
import { TagManager } from "./TagManager";
import { TodoList } from "./TodoList";
import { TodoForm } from "./TodoForm";

const defaultFilters: TodoFilters = {
  page: 1,
  page_size: 20,
  status: "all",
};

export function TodoPage() {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [filters, setFilters] = useState<TodoFilters>(defaultFilters);
  const { data, isLoading, error } = useTodos(filters);
  const { data: tags = [] } = useTags();
  const { user, logout } = useAuth();
  const pageSize = filters.page_size ?? 20;
  const page = filters.page ?? 1;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  const clearFilters = () => setFilters(defaultFilters);
  const goToPage = (nextPage: number) =>
    setFilters((current) => ({ ...current, page: nextPage }));

  return (
    <div className="min-h-screen bg-muted/40">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-xl font-bold">Todo App</h1>
            {user && <p className="text-sm text-muted-foreground">{user.email}</p>}
          </div>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle className="text-lg">My Todos</CardTitle>
            <Button size="sm" onClick={() => setShowCreateForm(true)}>
              <Plus className="mr-1 h-4 w-4" />
              Add Todo
            </Button>
          </CardHeader>
          <Separator />
          <CardContent className="space-y-5 pt-4">
            <TagManager tags={tags} />
            <TodoFiltersBar
              filters={filters}
              tags={tags}
              onChange={setFilters}
              onClear={clearFilters}
            />

            {isLoading && (
              <div className="py-12 text-center text-muted-foreground">
                Loading todos...
              </div>
            )}
            {error && (
              <div className="py-12 text-center text-destructive">
                Failed to load todos. Please try again.
              </div>
            )}
            {data && <TodoList todos={data.items} tags={tags} />}
            {data && data.total > 0 && (
              <div className="flex items-center justify-between gap-3 border-t pt-4 text-sm text-muted-foreground">
                <span>
                  Showing {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, data.total)} of {data.total}
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Previous page"
                    onClick={() => goToPage(page - 1)}
                    disabled={page <= 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="min-w-16 text-center text-xs">
                    Page {page} / {totalPages}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Next page"
                    onClick={() => goToPage(page + 1)}
                    disabled={page >= totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </main>

      <TodoForm
        mode="create"
        open={showCreateForm}
        onClose={() => setShowCreateForm(false)}
      />
    </div>
  );
}
