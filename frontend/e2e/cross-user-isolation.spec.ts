import { test, expect, type BrowserContext } from "@playwright/test";

async function signUpAndLogin(
  context: BrowserContext,
  email: string,
  password: string,
) {
  const page = await context.newPage();
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
  return page;
}

test("cross-user data isolation: user B cannot see user A private todo", async ({
  browser,
}) => {
  const userAContext = await browser.newContext();
  const userBContext = await browser.newContext();

  const userAPage = await signUpAndLogin(
    userAContext,
    `userA-${Date.now()}@example.com`,
    "Password@123",
  );
  await userAPage.getByRole("button", { name: "Add Todo" }).click();
  await userAPage.getByLabel("Title").fill("Private task");
  await userAPage.getByLabel("Description (optional)").fill("Only for user A");
  await userAPage.getByRole("button", { name: "Create", exact: true }).click();

  const userBPage = await signUpAndLogin(
    userBContext,
    `userB-${Date.now()}@example.com`,
    "Password@123",
  );
  await expect(userBPage.getByText("Private task")).toHaveCount(0);

  await userAPage.close();
  await userBPage.close();
});
