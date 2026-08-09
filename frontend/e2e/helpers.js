// @ts-check

async function loginAsOwner(page) {
  await page.goto('/login');
  // The very first login attempt against a webServer that just finished
  // booting can hit a transient "couldn't reach the server" — the backend
  // process is up (its /api/health readiness check passed) but a specific
  // request lands in the small window before it's fully warm. That's a
  // real, user-facing case (see Login.jsx's loginErrorMessage — this is
  // exactly the network-failure branch, not "wrong password"), and a real
  // user's answer is the same one this does: try again.
  for (let attempt = 1; attempt <= 3; attempt++) {
    await page.getByTestId('login-email').fill('owner@nua.com');
    await page.getByTestId('login-password').fill('NuaOwner2026!');
    await page.getByTestId('login-submit').click();
    try {
      await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 10_000 });
      return;
    } catch (e) {
      if (attempt === 3) throw e;
      await page.waitForTimeout(1500);
    }
  }
}

module.exports = { loginAsOwner };
