// @ts-check
const { test, expect } = require('@playwright/test');

test('a guest can place a pickup order and track it', async ({ page }) => {
  await page.goto('/order-online');
  await expect(page.getByTestId('order-online-page')).toBeVisible({ timeout: 15_000 });

  const firstItem = page.locator('[data-testid^="online-product-"]').first();
  await expect(firstItem).toBeVisible({ timeout: 15_000 });
  await firstItem.click();

  await expect(page.getByTestId('online-cart')).toBeVisible();
  await page.getByTestId('online-name').fill('E2E Guest');
  await page.getByTestId('online-phone').fill('0400000000');

  await page.getByTestId('place-order-btn').click();

  // place() navigates to /track/{id} once the order is accepted (or to a
  // Stripe checkout page if payments are configured for this venue — the
  // e2e backend has no Stripe keys set, so it always falls through to the
  // tracking page).
  await page.waitForURL(/\/track\//, { timeout: 15_000 });
  await expect(page.getByTestId('track-order-card')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId('track-step-pending')).toBeVisible();
});
