import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Pencil, Tag as TagIcon, Trash2, X } from "lucide-react";
import type { Tag } from "../api/tags";
import {
  useAttachTag,
  useDetachTag,
  type Todo,
} from "../api/todos";

interface TodoItemProps {
  todo: Todo;
  availableTags: Tag[];
  selected: boolean;
  onSelect: (id: string, selected: boolean) => void;
  onToggle: (todo: Todo) => void;
  onEdit: (todo: Todo) => void;
  onDelete: (id: string) => void;
}

export function TodoItem({
  todo,
  availableTags,
  selected,
  onSelect,
  onToggle,
  onEdit,
  onDelete,
}: TodoItemProps) {
  const attachTag = useAttachTag();
  const detachTag = useDetachTag();
  const attachedIds = new Set(todo.tags.map((tag) => tag.id));
  const unattachedTags = availableTags.filter((tag) => !attachedIds.has(tag.id));

  return (
    <div className="flex items-start gap-3 rounded-lg border bg-card p-3 transition-colors hover:bg-accent/50">
      <Checkbox
        checked={selected}
        onCheckedChange={(checked) => onSelect(todo.id, checked === true)}
        aria-label={`Select ${todo.title}`}
        className="mt-0.5"
      />
      <Checkbox
        id={`todo-${todo.id}`}
        data-testid="todo-completion"
        checked={todo.completed}
        onCheckedChange={() => onToggle(todo)}
        aria-label={`Toggle completion for ${todo.title}`}
        className="mt-0.5"
      />

      <div className="min-w-0 flex-1">
        <label
          htmlFor={`todo-${todo.id}`}
          className={`cursor-pointer text-sm font-medium ${
            todo.completed ? "text-muted-foreground line-through" : ""
          }`}
        >
          {todo.title}
        </label>
        {todo.description && (
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {todo.description}
          </p>
        )}
        <div className="mt-2 flex flex-wrap items-center gap-1">
          {todo.tags.map((tag) => (
            <span
              key={tag.id}
              className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px]"
            >
              <span
                className="h-2 w-2 rounded-full border"
                style={{ backgroundColor: tag.color || "transparent" }}
                aria-hidden="true"
              />
              {tag.name}
              <button
                type="button"
                className="rounded-full text-muted-foreground hover:text-foreground"
                onClick={() => detachTag.mutate({ todoId: todo.id, tagId: tag.id })}
                aria-label={`Remove ${tag.name} from ${todo.title}`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          {unattachedTags.length > 0 && (
            <label className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <TagIcon className="h-3 w-3" />
              <span className="sr-only">Add tag to {todo.title}</span>
              <select
                className="max-w-28 bg-transparent text-xs outline-none"
                value=""
                onChange={(event) => {
                  if (event.target.value) {
                    attachTag.mutate({ todoId: todo.id, tagId: event.target.value });
                  }
                }}
                aria-label={`Add tag to ${todo.title}`}
              >
                <option value="">Add tag</option>
                {unattachedTags.map((tag) => (
                  <option key={tag.id} value={tag.id}>
                    {tag.name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => onEdit(todo)}
          aria-label={`Edit ${todo.title}`}
        >
          <Pencil className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-destructive hover:text-destructive"
          onClick={() => onDelete(todo.id)}
          aria-label={`Delete ${todo.title}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
