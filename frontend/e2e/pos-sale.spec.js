// @ts-check
const { test, expect } = require('@playwright/test');
const { loginAsOwner } = require('./helpers');

// POS is one of the heaviest lazy-loaded routes (products, floor tables,
// wallet data all load on mount) and this is its first-ever navigation in a
// fresh browser context, so its chunk hasn't been fetched yet either — give
// this one noticeably more runway than the suite default.
test.setTimeout(60_000);

test('ring up a card sale end to end', async ({ page }) => {
  await loginAsOwner(page);
  await page.goto('/pos', { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await expect(page.getByTestId('pos-terminal')).toBeVisible({ timeout: 20_000 });

  // Add the first available product tile to the cart — the alcohol catalog
  // seeds on every fresh boot, so at least one product-* tile always exists
  // without depending on a specific product name.
  const firstProduct = page.locator('[data-testid^="product-"]').first();
  await expect(firstProduct).toBeVisible({ timeout: 15_000 });
  await firstProduct.click();

  // Cart total should now be non-zero.
  await expect(page.getByTestId('pos-total')).not.toHaveText('$0.00');

  await page.getByTestId('pos-proceed-payment').click();
  await expect(page.getByTestId('payment-methods-panel')).toBeVisible();
  await page.getByTestId('pay-card').click();

  // The "Transaction Complete!" toast is transient (sonner auto-dismisses
  // it), so asserting on it directly races its own disappearance on a slow
  // CI runner. The cart clearing back to empty is the durable, checkable
  // consequence of the same successful checkout — assert on that instead.
  await expect(page.getByTestId('pos-total')).toHaveText('$0.00', { timeout: 15_000 });
});
