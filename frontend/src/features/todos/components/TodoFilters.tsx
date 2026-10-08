import { FilterX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Tag } from "../api/tags";
import type { TodoFilters as TodoFiltersState } from "../api/todos";

interface TodoFiltersProps {
  filters: TodoFiltersState;
  tags: Tag[];
  onChange: (filters: TodoFiltersState) => void;
  onClear: () => void;
}

export function TodoFilters({
  filters,
  tags,
  onChange,
  onClear,
}: TodoFiltersProps) {
  const update = (change: Partial<TodoFiltersState>) =>
    onChange({ ...filters, ...change, page: 1 });

  return (
    <section className="space-y-3 border-b pb-4" aria-label="Todo filters">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Filter todos</p>
        <Button type="button" variant="ghost" size="sm" onClick={onClear}>
          <FilterX className="mr-1 h-4 w-4" />
          Clear filters
        </Button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-1">
          <Label htmlFor="todo-keyword">Keyword</Label>
          <Input
            id="todo-keyword"
            value={filters.keyword ?? ""}
            onChange={(event) => update({ keyword: event.target.value })}
            placeholder="Search title or description"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="todo-status">Status</Label>
          <select
            id="todo-status"
            className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
            value={filters.status ?? "all"}
            onChange={(event) =>
              update({
                status: event.target.value as "active" | "completed" | "all",
              })
            }
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="todo-tag">Tag</Label>
          <select
            id="todo-tag"
            className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
            value={filters.tag_id ?? ""}
            onChange={(event) => update({ tag_id: event.target.value || undefined })}
          >
            <option value="">All tags</option>
            {tags.map((tag) => (
              <option value={tag.id} key={tag.id}>
                {tag.name}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label htmlFor="todo-date-from">From</Label>
            <Input
              id="todo-date-from"
              type="date"
              value={filters.date_from ?? ""}
              onChange={(event) => update({ date_from: event.target.value || undefined })}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="todo-date-to">To</Label>
            <Input
              id="todo-date-to"
              type="date"
              value={filters.date_to ?? ""}
              onChange={(event) => update({ date_to: event.target.value || undefined })}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
