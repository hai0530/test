import { test, expect } from "@playwright/test";

test("full user journey: register, login, create todo, toggle complete, logout", async ({
  page,
}) => {
  const email = `flow-${Date.now()}@example.com`;
  const password = "Password@123";

  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm Password").fill(password);
  await page.getByRole("button", { name: "Create Account" }).click();

  await expect(page.getByRole("button", { name: "Add Todo" })).toBeVisible({
    timeout: 15_000,
  });

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page.getByRole("button", { name: "Add Todo" })).toBeVisible({
    timeout: 15_000,
  });

  await page.getByRole("button", { name: "Add Todo" }).click();
  await page.getByLabel("Title").fill("Playwright todo");
  await page.getByLabel("Description (optional)").fill("Created via E2E");
  await page.getByRole("button", { name: "Create", exact: true }).click();

  await expect(page.getByText("Playwright todo")).toBeVisible();
  const todoCheckbox = page.getByTestId("todo-completion");
  await todoCheckbox.click();
  await expect(todoCheckbox).toBeChecked();

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login$/);
});
