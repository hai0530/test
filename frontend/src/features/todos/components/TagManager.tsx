import { useEffect, useState } from "react";
import { Pencil, Plus, Trash2, X } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useCreateTag,
  useDeleteTag,
  useUpdateTag,
  type Tag,
} from "../api/tags";
import { tagSchema, type TagFormData } from "../schemas/tag";

interface TagManagerProps {
  tags: Tag[];
}

export function TagManager({ tags }: TagManagerProps) {
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const createTag = useCreateTag();
  const updateTag = useUpdateTag();
  const deleteTag = useDeleteTag();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TagFormData>({
    resolver: zodResolver(tagSchema),
    defaultValues: { name: "", color: "" },
  });

  useEffect(() => {
    reset({ name: editingTag?.name ?? "", color: editingTag?.color ?? "" });
  }, [editingTag, reset]);

  const onSubmit = (data: TagFormData) => {
    const payload = { name: data.name, color: data.color || null };
    if (editingTag) {
      updateTag.mutate(
        { id: editingTag.id, data: payload },
        { onSuccess: () => setEditingTag(null) },
      );
    } else {
      createTag.mutate(payload, { onSuccess: () => reset() });
    }
  };

  const isPending = createTag.isPending || updateTag.isPending;

  return (
    <section className="space-y-3" aria-label="Tag management">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Tags</h2>
        {editingTag && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Cancel tag editing"
            onClick={() => setEditingTag(null)}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      <form onSubmit={handleSubmit(onSubmit)} className="grid gap-2 sm:grid-cols-[1fr_7rem_auto]">
        <div>
          <Label className="sr-only" htmlFor="tag-name">
            Tag name
          </Label>
          <Input id="tag-name" placeholder="Tag name" {...register("name")} />
          {errors.name && (
            <p className="mt-1 text-xs text-destructive">{errors.name.message}</p>
          )}
        </div>
        <div>
          <Label className="sr-only" htmlFor="tag-color">
            Tag color
          </Label>
          <Input id="tag-color" type="color" {...register("color")} />
        </div>
        <Button type="submit" disabled={isPending} aria-label={editingTag ? "Save tag" : "Create tag"}>
          {editingTag ? "Save" : <Plus className="h-4 w-4" />}
        </Button>
      </form>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <div
            key={tag.id}
            className="inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs"
          >
            <span
              className="h-2.5 w-2.5 rounded-full border"
              style={{ backgroundColor: tag.color || "transparent" }}
              aria-hidden="true"
            />
            <span>{tag.name}</span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              aria-label={`Edit ${tag.name}`}
              onClick={() => setEditingTag(tag)}
            >
              <Pencil className="h-3 w-3" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-5 w-5 text-destructive hover:text-destructive"
              aria-label={`Delete ${tag.name}`}
              onClick={() => deleteTag.mutate(tag.id)}
              disabled={deleteTag.isPending}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        ))}
      </div>
    </section>
  );
}
