import { expect, test } from "@playwright/test";

test("home page reaches the API", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "NutriRoll" })).toBeVisible();
  await expect(page.getByRole("status")).toContainText(/API OK/i, { timeout: 10_000 });
});
