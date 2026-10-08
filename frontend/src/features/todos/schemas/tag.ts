import { z } from "zod";

export const tagSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(50, "Name is too long"),
  color: z
    .string()
    .trim()
    .max(20, "Color is too long")
    .optional()
    .or(z.literal("")),
});

export type TagFormData = z.infer<typeof tagSchema>;
