// @ts-check

async function loginAsOwner(page) {
  await page.goto('/login');
  await page.getByTestId('login-email').fill('owner@nua.com');
  await page.getByTestId('login-password').fill('NuaOwner2026!');
  await page.getByTestId('login-submit').click();
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 20_000 });
}

module.exports = { loginAsOwner };
