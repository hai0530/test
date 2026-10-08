import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";

export interface Tag {
  id: string;
  user_id: string;
  name: string;
  color: string | null;
  created_at: string;
  updated_at: string;
}

export interface TagInput {
  name: string;
  color?: string | null;
}

export function useTags() {
  return useQuery({
    queryKey: ["tags"],
    queryFn: async (): Promise<Tag[]> => {
      const response = await api.get("/tags");
      return response.data;
    },
  });
}

function invalidateTagData() {
  void queryClient.invalidateQueries({ queryKey: ["tags"] });
  void queryClient.invalidateQueries({ queryKey: ["todos"] });
}

export function useCreateTag() {
  return useMutation({
    mutationFn: async (data: TagInput): Promise<Tag> => {
      const response = await api.post("/tags", data);
      return response.data;
    },
    onSuccess: () => {
      invalidateTagData();
      toast.success("Tag created");
    },
    onError: () => toast.error("Unable to create tag"),
  });
}

export function useUpdateTag() {
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: TagInput }): Promise<Tag> => {
      const response = await api.patch(`/tags/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      invalidateTagData();
      toast.success("Tag updated");
    },
    onError: () => toast.error("Unable to update tag"),
  });
}

export function useDeleteTag() {
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await api.delete(`/tags/${id}`);
    },
    onSuccess: () => {
      invalidateTagData();
      toast.success("Tag deleted");
    },
    onError: () => toast.error("Unable to delete tag"),
  });
}
