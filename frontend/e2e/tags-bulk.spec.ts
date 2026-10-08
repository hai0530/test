import { test, expect } from "@playwright/test";

async function createUserAndLogin(page: import("@playwright/test").Page) {
  const email = `tags-${Date.now()}@example.com`;
  const password = "Password@123";

  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm Password").fill(password);
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page.getByRole("button", { name: "Add Todo" })).toBeVisible({
    timeout: 15_000,
  });
}

test("tags can filter todos and bulk status updates are persisted", async ({
  page,
}) => {
  await createUserAndLogin(page);

  await page.getByRole("button", { name: "Create tag" }).click();
  await expect(page.getByText("Name is required")).toBeVisible();
  await page.getByLabel("Tag name").fill("Urgent");
  await page.getByRole("button", { name: "Create tag" }).click();
  await expect(
    page.getByRole("region", { name: "Tag management" }).getByText("Urgent"),
  ).toBeVisible();

  for (const title of ["First task", "Second task"]) {
    await page.getByRole("button", { name: "Add Todo" }).click();
    await page.getByLabel("Title").fill(title);
    await page.getByRole("button", { name: "Create", exact: true }).click();
    await expect(page.getByText(title, { exact: true })).toBeVisible();
  }

  await page.getByLabel("Add tag to First task").selectOption({ label: "Urgent" });
  await expect(
    page.getByRole("button", { name: "Remove Urgent from First task" }),
  ).toBeVisible();

  await page.getByRole("checkbox", { name: "Select First task" }).check();
  await page.getByRole("checkbox", { name: "Select Second task" }).check();
  await page.getByRole("button", { name: "Complete" }).click();
  await expect(
    page.getByRole("checkbox", { name: "Toggle completion for First task" }),
  ).toBeChecked();
  await expect(
    page.getByRole("checkbox", { name: "Toggle completion for Second task" }),
  ).toBeChecked();

  const tagSelector = page.getByLabel("Tag", { exact: true });
  await tagSelector.selectOption({ label: "Urgent" });
  await expect(page.getByText("First task", { exact: true })).toBeVisible();
  await expect(page.getByText("Second task", { exact: true })).toHaveCount(0);

  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.getByText("First task", { exact: true })).toBeVisible();
  await expect(page.getByText("Second task", { exact: true })).toBeVisible();
});
