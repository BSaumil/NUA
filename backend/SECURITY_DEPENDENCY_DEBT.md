# Backend dependency vulnerability debt

`pip-audit -r requirements.txt` is now wired into CI (see `.github/workflows/ci.yml`) and runs on every PR. As of 2026-09-14 it reports 152 known advisories across the pinned dependency set. This file tracks what's been fixed and what's deliberately deferred, so the CI step's output is honest and traceable rather than either silently suppressed or blocking merges on a scope this pass didn't cover.

## Fixed in this pass (bumped, full test suite re-run green: 468 passed / 0 failed)

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
| ecdsa | 0.19.1 | 0.19.2 | Patch bump. |
| pyasn1 | 0.6.1 | 0.6.4 | Patch bump. |
| httplib2 | 0.31.2 | 0.32.0 | Patch bump. |

## Deliberately deferred — needs its own tested pass, not bundled into P0 security work

These are framework-level or otherwise higher-blast-radius packages where a version bump risks real breaking changes (FastAPI/Starlette compatibility, PyMongo/Motor wire-protocol behavior, cryptography's API churn across majors). Bumping them safely means reading each changelog, upgrading one at a time, and re-running the full suite plus a manual smoke test — that's a dedicated task, not a rider on this pass.

| Package | Current | Advisories | Note |
|---|---|---|---|
| `starlette` | 0.37.2 | multiple (up to 1.3.x fixes) | FastAPI's version pin constrains how far this can move without also bumping FastAPI itself — needs a coordinated bump + full regression pass. |
| `cryptography` | 46.0.3 | multiple (up to 50.0.0) | Used for JWT/crypto-adjacent operations; high-value to fix, but `cryptography` majors have real API churn — needs its own tested pass. |
| `aiohttp` | 3.13.5 | multiple (up to 3.14.3) | Used by outbound integrations; check call sites for behavior changes before bumping. |
| `pymongo` | 4.5.0 | 1 (4.6.3) | Bumping this also touches `motor`'s compatibility matrix — verify against the pinned `motor` version before moving. |
| `pillow` | 12.2.0 | multiple (up to 12.3.0) | Used for image handling (e.g. receipt/QR generation) — low risk bump, deferred only for time, not risk. |
| `pypdf` | 6.14.2 | multiple (up to 6.16.1) | Used for PDF export (BAS reports, receipts) — low risk bump, deferred only for time. |
| `black`, `pytest` | pinned versions with advisories | — | Dev-only tooling, never executes against untrusted input in production — lowest priority. |

## Recommended next step

Bump `pypdf` and `pillow` next (low risk, same pattern as this pass), then schedule a dedicated task for `starlette`/`cryptography`/`aiohttp`/`pymongo` that upgrades one package per commit with a full test run between each.
