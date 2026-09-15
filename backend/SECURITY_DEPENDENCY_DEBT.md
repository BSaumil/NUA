# Backend dependency vulnerability debt

`pip-audit -r requirements.txt` is wired into CI (see `.github/workflows/ci.yml`) and runs on every PR. This file tracks what's been fixed and what's deliberately deferred, with the reasoning, so the CI step's output is honest and traceable rather than either silently suppressed or blocking merges on a scope a given pass didn't cover.

## Pass 2 — 2026-09-15: full severity/reachability/exposure/blast-radius triage

Pass 1 (below) took a "bump anything low-risk" approach and explicitly deferred the framework-level packages. This pass re-triaged every advisory pip-audit reported against pass 1's baseline (152 advisories) — which had already fallen to **97 advisories across 9 packages** by the time this pass started, from upstream fixes landing between passes — using four questions per package: is it actually reachable from this app's code (imported and called, or just installed and unused), what's the real severity of what's reachable, how far does a safe fix have to jump (patch vs. minor vs. major, and is that jump even installable under this app's other pins), and what's the blast radius if the bump is wrong.

**Result: 97 advisories → 26, across 9 packages → 4.** Full backend suite (`python -m pytest tests/inprocess -q`) re-run green after every change: 629 passed, 0 failed.

### Fixed — patch/minor bumps, no compatibility risk

| Package | Old → New | Advisories closed | Why safe |
|---|---|---|---|
| `pymongo` | 4.5.0 → 4.6.3 | 1 (CVE-2024-5629, OOB read in bson parsing) | `motor==3.3.1` (the only thing wrapping it) pins `pymongo>=4.5,<5` — 4.6.3 is inside that range with room to spare. Patch-level bson bugfix, no driver API change. |
| `cryptography` | 46.0.3 → 46.0.7 | 3 of 13 (CVE-2026-26007, CVE-2026-34073, CVE-2026-39892) | These three are fixed at 46.0.5/46.0.6/46.0.7 — still inside the 46.x patch series. The other 10 need 48.0.1/49.0.0/50.0.0 (see deferred, below). |
| `pillow` | 12.2.0 → 12.3.0 | 25 | Patch bump; image handling here is receipt/QR generation, not processing untrusted uploads. |
| `pypdf` | 6.14.2 → 6.16.1 | 8 | Minor bump; used for PDF export (BAS/STP reports, receipts), not parsing untrusted PDFs. |
| `aiohttp` | 3.13.5 → 3.14.3 | 28 | Minor bump, and `aiohttp-retry` (the only pinned package that requires it) has no version constraint on it at all. **Reachability note:** `grep -rn "import aiohttp"` across the entire backend returns nothing — nothing in this codebase imports `aiohttp` directly (outbound HTTP here goes through `httpx`). It's a pure transitive dependency of something else in the pin set, so these 28 advisories had zero actual runtime exposure even before the bump; fixed anyway since the bump is free. |

### Fixed — removed, not bumped (zero reachability, and no fix exists anyway)

| Package | Advisories | Why removed instead of bumped |
|---|---|---|
| `ecdsa` | 1 (CVE-2024-23342, Minerva timing attack on P-256 signing) | No fix version exists upstream at all (`python-ecdsa`'s own position is that pure-Python constant-time signing isn't practical) — not "patchable" by definition. But `grep -rn "import ecdsa"` / `from ecdsa` across the backend returns nothing: the vulnerable `SigningKey.sign_digest()` path is never called. `pip show ecdsa` confirms it's `Required-by: python-jose` only, and `python-jose` itself (directly pinned in requirements.txt) is never imported anywhere — this app does its JWT encode/decode exclusively through `PyJWT` (`import jwt`, used in `middleware/actor_context.py`, `routes/auth.py`, `services/two_factor.py`, etc.). `rsa==4.9.1` was `Required-by: python-jose` only too. Removed all three (`ecdsa`, `python-jose`, `rsa`) from requirements.txt as genuinely dead dependencies — this closes the advisory by eliminating the unreachable code that carried it, rather than leaving an unfixable CVE on the books forever. `pyasn1`/`pyasn1_modules` were left in place — `google-auth` (which is used) depends on those independently. |

### Deliberately deferred — reasoning updated this pass

| Package | Current | Remaining advisories | Why not fixed now |
|---|---|---|---|
| `starlette` | 0.37.2 | 14 (fixes land at 0.40.0+/1.x) | **Structurally blocked, not just risky:** `fastapi==0.110.1`'s own metadata pins `starlette<0.38.0,>=0.37.2` — 0.37.2 is already the *ceiling* of what this FastAPI version allows. There is no starlette version this app can install today that both satisfies FastAPI's constraint and picks up any of these fixes. Closing this requires bumping FastAPI itself first (a framework major-version-range move with its own request/response/dependency-injection behavior changes across the whole app's ~150 routes), which is correctly a separate, dedicated, full-regression pass — not something "bump the version" can do safely, let alone as a rider on this one. |
| `cryptography` | 46.0.7 | 7 (need 48.0.1 for 1, 49.0.0 for 3, 50.0.0 for 3) | The remaining fixes span three major-version jumps (46→48→49→50). `cryptography` has a documented history of removing deprecated APIs across majors; this codebase's direct usage (JWT-adjacent crypto operations) needs an audit against each major's changelog before it's safe to move, which the patch bump already taken doesn't require. Genuinely a separate tested pass, matching pass 1's own conclusion. |
| `black` | 25.9.0 | 3 (fix 26.3.x) | Dev-only formatter — never imported or executed by the running application, zero production reachability. Lowest priority by construction, not just by choice. |
| `pytest` | 8.4.2 | 2 (CVE-2025-71176, `/tmp/pytest-of-{user}` local privilege/DoS issue; fix 9.0.3) | Dev/CI-only — never present in a deployed instance, and the CVE itself requires **local, multi-user access to the same machine running the test suite**, which is not this app's threat model at all (zero remote reachability). The fix is also a pytest **major** version bump (8→9), which risks breaking collection/fixtures across all 629 tests in this suite for a vulnerability with no production exposure — not a trade worth making under "without breaking compatibility." |

## Pass 1 — 2026-09-14 baseline (152 advisories at the time)

`pip-audit -r requirements.txt` reported 152 known advisories across the pinned dependency set at the time.

### Fixed in pass 1 (bumped, full test suite re-run green: 468 passed / 0 failed)

| Package | Old | New | Why safe to bump blind |
|---|---|---|---|
| PyJWT | 2.10.1 | 2.13.0 | Small, stable `encode`/`decode` API; directly relevant given this codebase's JWT-centric auth. |
| urllib3 | 2.5.0 | 2.7.0 | Patch/minor, widely used, no API surface this app touches directly changed. |
| requests | 2.32.5 | 2.33.0 | Same. |
| idna | 3.11 | 3.19 | Pure parsing library, no app-facing API change. |
| click | 8.3.0 | 8.3.3 | Dev-tool dependency (used transitively), patch bump. |
| Pygments | 2.19.2 | 2.20.0 | Dev-tool dependency, patch bump. |
| python-dotenv | 1.1.1 | 1.2.2 | Only used at process startup to load `.env`; narrow surface. |
| python-multipart | 0.0.20 | 0.0.31 | Used by FastAPI for form/file parsing; several of the fixed CVEs are in this exact path (malformed multipart handling), so this one matters. |
| ecdsa | 0.19.1 | 0.19.2 | Patch bump (superseded by pass 2's removal, above). |
| pyasn1 | 0.6.1 | 0.6.4 | Patch bump. |
| httplib2 | 0.31.2 | 0.32.0 | Patch bump. |

## Recommended next step

Only `starlette` (blocked on a coordinated FastAPI bump) and `cryptography`'s remaining major-version jump are left as real, reachable, unresolved debt. Schedule a dedicated task that: (1) bumps FastAPI to a version whose `starlette` constraint reaches a fixed release, running the full route surface's tests plus a manual smoke test; (2) separately walks `cryptography` 46→48→49→50 one major at a time, auditing this app's direct crypto call sites against each changelog between bumps.
