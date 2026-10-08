import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";

export interface TodoTag {
  id: string;
  name: string;
  color: string | null;
}

export interface Todo {
  id: string;
  title: string;
  description: string | null;
  completed: boolean;
  user_id: string;
  created_at: string;
  updated_at: string;
  tags: TodoTag[];
}

export interface TodoListResponse {
  items: Todo[];
  total: number;
  page: number;
  size: number;
}

export interface TodoFilters {
  page?: number;
  page_size?: number;
  status?: "active" | "completed" | "all";
  tag_id?: string;
  keyword?: string;
  date_from?: string;
  date_to?: string;
}

export interface CreateTodoRequest {
  title: string;
  description?: string;
}

export interface UpdateTodoRequest {
  title?: string;
  description?: string;
  completed?: boolean;
}

const defaultFilters: Required<Pick<TodoFilters, "page" | "page_size">> = {
  page: 1,
  page_size: 20,
};

export function normalizeTodoFilters(filters: TodoFilters = {}) {
  return {
    page: filters.page ?? defaultFilters.page,
    page_size: filters.page_size ?? defaultFilters.page_size,
    status: filters.status ?? "all",
    tag_id: filters.tag_id ?? "",
    keyword: filters.keyword?.trim() ?? "",
    date_from: filters.date_from ?? "",
    date_to: filters.date_to ?? "",
  } as const;
}

export function todosQueryKey(filters: TodoFilters = {}) {
  return ["todos", normalizeTodoFilters(filters)] as const;
}

export function useTodos(filters: TodoFilters = {}) {
  const normalized = normalizeTodoFilters(filters);
  return useQuery({
    queryKey: todosQueryKey(normalized),
    queryFn: async (): Promise<TodoListResponse> => {
      const params = Object.fromEntries(
        Object.entries(normalized).filter(([, value]) => value !== ""),
      );
      const response = await api.get("/todos", { params });
      return response.data;
    },
  });
}

function invalidateTodos() {
  return queryClient.invalidateQueries({ queryKey: ["todos"] });
}

export function useCreateTodo() {
  return useMutation({
    mutationFn: async (data: CreateTodoRequest): Promise<Todo> => {
      const response = await api.post("/todos", data);
      return response.data;
    },
    onSuccess: () => {
      void invalidateTodos();
      toast.success("Todo created successfully!");
    },
    onError: () => toast.error("Failed to create todo"),
  });
}

export function useUpdateTodo() {
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: UpdateTodoRequest;
    }): Promise<Todo> => {
      const response = await api.put(`/todos/${id}`, data);
      return response.data;
    },
    onSuccess: () => void invalidateTodos(),
    onError: () => toast.error("Failed to update todo"),
  });
}

export function useDeleteTodo() {
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await api.delete(`/todos/${id}`);
    },
    onSuccess: () => {
      void invalidateTodos();
      toast.success("Todo deleted successfully!");
    },
    onError: () => toast.error("Failed to delete todo"),
  });
}

export function useToggleTodo() {
  const updateTodo = useUpdateTodo();

  return {
    ...updateTodo,
    mutate: (todo: Todo) => {
      updateTodo.mutate({
        id: todo.id,
        data: { completed: !todo.completed },
      });
    },
  };
}

export function useAttachTag() {
  return useMutation({
    mutationFn: async ({ todoId, tagId }: { todoId: string; tagId: string }) => {
      const response = await api.post(`/todos/${todoId}/tags`, { tag_id: tagId });
      return response.data as Todo;
    },
    onSuccess: () => void invalidateTodos(),
    onError: () => toast.error("Failed to attach tag"),
  });
}

export function useDetachTag() {
  return useMutation({
    mutationFn: async ({ todoId, tagId }: { todoId: string; tagId: string }) => {
      await api.delete(`/todos/${todoId}/tags/${tagId}`);
    },
    onSuccess: () => void invalidateTodos(),
    onError: () => toast.error("Failed to detach tag"),
  });
}

export function useBulkUpdateStatus() {
  return useMutation({
    mutationFn: async ({ todoIds, completed }: { todoIds: string[]; completed: boolean }) => {
      const response = await api.patch("/todos/bulk-status", {
        todo_ids: todoIds,
        completed,
      });
      return response.data as { updated_count: number };
    },
    onSuccess: () => {
      void invalidateTodos();
      toast.success("Todos updated successfully");
    },
    onError: () => toast.error("Failed to update selected todos"),
  });
}
