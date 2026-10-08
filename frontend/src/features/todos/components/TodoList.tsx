import { useMemo, useState } from "react";
import { CheckCheck, Circle, SquareCheck } from "lucide-react";
import { TodoItem } from "./TodoItem";
import { TodoForm } from "./TodoForm";
import type { Tag } from "../api/tags";
import type { Todo } from "../api/todos";
import { useBulkUpdateStatus, useDeleteTodo, useToggleTodo } from "../api/todos";

interface TodoListProps {
  todos: Todo[];
  tags: Tag[];
}

export function TodoList({ todos, tags }: TodoListProps) {
  const [editingTodo, setEditingTodo] = useState<Todo | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const deleteTodo = useDeleteTodo();
  const toggleTodo = useToggleTodo();
  const bulkUpdate = useBulkUpdateStatus();
  const todoIds = useMemo(() => new Set(todos.map((todo) => todo.id)), [todos]);
  const selectedOnPage = todos.filter((todo) => selectedIds.has(todo.id)).length;

  const setSelected = (id: string, selected: boolean) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (selected) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedOnPage === todos.length) {
      setSelectedIds((current) => {
        const next = new Set(current);
        todos.forEach((todo) => next.delete(todo.id));
        return next;
      });
    } else {
      setSelectedIds((current) => new Set([...current, ...todoIds]));
    }
  };

  const updateSelected = (completed: boolean) => {
    const ids = [...selectedIds].filter((id) => todoIds.has(id));
    if (ids.length === 0) return;
    bulkUpdate.mutate({ todoIds: ids, completed }, {
      onSuccess: () => setSelectedIds(new Set()),
    });
  };

  if (todos.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        <p className="text-lg">No todos match these filters</p>
        <p className="mt-1 text-sm">Try clearing a filter or create a new todo.</p>
      </div>
    );
  }

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-2 border-b pb-3">
        <button
          type="button"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          onClick={selectAll}
          aria-label={selectedOnPage === todos.length ? "Clear selection" : "Select all todos"}
        >
          {selectedOnPage === todos.length ? (
            <SquareCheck className="h-4 w-4" />
          ) : (
            <Circle className="h-4 w-4" />
          )}
          {selectedOnPage === todos.length ? "Clear selection" : "Select page"}
        </button>
        {selectedOnPage > 0 && (
          <>
            <span className="text-xs text-muted-foreground">{selectedOnPage} selected</span>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-accent"
              onClick={() => updateSelected(true)}
              disabled={bulkUpdate.isPending}
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Complete
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-accent"
              onClick={() => updateSelected(false)}
              disabled={bulkUpdate.isPending}
            >
              <Circle className="h-3.5 w-3.5" />
              Mark active
            </button>
          </>
        )}
      </div>
      <div className="space-y-2">
        {todos.map((todo) => (
          <TodoItem
            key={todo.id}
            todo={todo}
            availableTags={tags}
            selected={selectedIds.has(todo.id)}
            onSelect={setSelected}
            onToggle={(item) => toggleTodo.mutate(item)}
            onEdit={setEditingTodo}
            onDelete={(id) => deleteTodo.mutate(id)}
          />
        ))}
      </div>
      {editingTodo && (
        <TodoForm
          mode="edit"
          todo={editingTodo}
          open={!!editingTodo}
          onClose={() => setEditingTodo(null)}
        />
      )}
    </>
  );
}
