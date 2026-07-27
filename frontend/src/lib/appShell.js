// Same backend, same build, different front door — decide which "app"
// this page load is acting as, purely from where it was loaded. This is
// what lets app.nuapos.com.au / staff.nuapos.com.au / owner.nuapos.com.au
// all serve the exact same React bundle (one source of truth) while
// behaving like three distinct apps.
//
// Resolution order: explicit ?shell= query param (demo/QA convenience) >
// a saved override in localStorage (lets a device "become" the staff/owner
// app without re-typing the URL each time) > the subdomain prefix > default
// to the main POS shell.
const VALID = ['pos', 'staff', 'owner'];

export function getAppShell() {
  try {
    const params = new URLSearchParams(window.location.search);
    const fromQuery = params.get('shell');
    if (fromQuery && VALID.includes(fromQuery)) {
      localStorage.setItem('nua_app_shell', fromQuery);
      return fromQuery;
    }

    const saved = localStorage.getItem('nua_app_shell');
    if (saved && VALID.includes(saved)) return saved;

    const host = window.location.hostname || '';
    if (host.startsWith('staff.')) return 'staff';
    if (host.startsWith('owner.')) return 'owner';
    return 'pos';
  } catch {
    return 'pos';
  }
}

export function setAppShell(shell) {
  if (!VALID.includes(shell)) return;
  try { localStorage.setItem('nua_app_shell', shell); } catch { /* noop */ }
}
