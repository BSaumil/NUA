# Nua on Railway — The 5-Year-Old Deployment Guide

Railway is like having a **friendly helper who reads your code and figures everything out**. You just point Railway at your GitHub repo, click some buttons, and ~10 minutes later your app is live. No Linux commands needed.

> **Why Railway vs Fly.io?**
> • Railway: **easiest** — point-and-click UI, auto-detects Node/Python, includes a database.
> • Fly.io: **more control + cheaper at scale**, but you write `fly.toml` and use a CLI.
>
> If you've never deployed anything before → use Railway.
> If you're comfy with a terminal and want to save money long-term → use Fly.io (see `/app/Fly.io Setup.md`).

---

## 🧰 Step 0 — Get your accounts ready (5 minutes)

| Sign up | Why |
|---|---|
| https://railway.com | Hosts the app |
| https://github.com | Holds the code (use Emergent's "Save to GitHub" button) |

That's it. No CLI install. No Docker. No Linux. Just a browser.

---

## 📦 Step 1 — Save your code to GitHub

In the Emergent chat input box, click the **"Save to GitHub"** option.
Follow the prompts → you'll end up with a repo like `github.com/yourname/nua`.

> Railway reads code from GitHub. So this MUST happen first.

---

## 🚀 Step 2 — Spin up the project on Railway

1. Go to https://railway.com and click **+ New Project**.
2. Choose **Deploy from GitHub repo**.
3. Pick your `nua` repo.
4. Railway will say "What do you want to deploy?" — for now click **Empty Project** so we can add services one at a time.

---

## 📦 Step 3 — Add MongoDB (1 click)

Inside your new Railway project:

1. Click **+ Create → Database → Add MongoDB**.
2. Railway provisions a MongoDB instance in ~30 seconds.
3. Click the new Mongo box → **Variables** tab → copy the value of `MONGO_URL` (looks like `mongodb://mongo:password@containers-us-west-X.railway.app:7654`).

Keep that string ready — we'll paste it into the backend in Step 4.

---

## 🧠 Step 4 — Add the Backend service

1. In the same project, click **+ Create → GitHub Repo** → pick your repo again.
2. After it loads, click the new service → **Settings**:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt && pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips '*'`
3. Click the **Variables** tab → **+ New Variable**. Add these one by one:

| Variable name | Value |
|---|---|
| `MONGO_URL` | *(paste the value from Step 3)* |
| `DB_NAME` | `nua_restaurant` |
| `JWT_SECRET` | *click "Generate" — Railway makes a random one* |
| `EMERGENT_LLM_KEY` | *paste your key from Emergent → Profile → Universal Key* |
| `FRONTEND_URL` | `https://nua-frontend.up.railway.app` *(we'll fix this in Step 6)* |
| `PORT` | `8001` |

4. **Networking** tab → click **Generate Domain**. Railway gives you something like `nua-backend-production.up.railway.app`. **Copy this URL.**

5. Wait ~3 minutes for the first deploy. Open `https://YOUR-BACKEND.up.railway.app/api/social/platforms` in your browser — you'll see `{"detail":"Not authenticated"}` which means **it's working** (it's just asking for a login).

---

## 🎨 Step 5 — Add the Frontend service

1. **+ Create → GitHub Repo** → same repo again.
2. New service → **Settings**:
   - **Root Directory**: `frontend`
   - **Build Command**: `yarn install --frozen-lockfile && yarn build`
   - **Start Command**: `npx serve -s build -l $PORT`

   *(`serve` ships with the `npx` shim, so no extra deps needed.)*

3. **Variables** tab — add:

| Variable name | Value |
|---|---|
| `REACT_APP_BACKEND_URL` | `https://YOUR-BACKEND.up.railway.app` *(from Step 4)* |
| `PORT` | `3000` |
| `NODE_ENV` | `production` |

> ⚠️ **Most common mistake**: `REACT_APP_BACKEND_URL` MUST be set BEFORE the first build. If you set it after, click **Deployments → Redeploy**.

4. **Networking** tab → **Generate Domain**. Note the URL (e.g. `nua-frontend-production.up.railway.app`).

5. Wait ~5 minutes. Open the frontend URL in your browser. 🎉
   Log in with `owner@nuva.com` / `NuvaOwner2026!`.

---

## 🔁 Step 6 — Sync the backend's `FRONTEND_URL`

Go back to the **Backend service → Variables** and change `FRONTEND_URL` to the real frontend URL from Step 5. Railway auto-redeploys. ~1 minute.

---

## 🌐 Step 7 — Add your own domain (optional)

If you bought `nua-eatery.com`:

### On Railway:
1. Frontend service → **Settings → Networking → Custom Domain** → type `nua-eatery.com` → click **Add Domain**.
2. Railway shows you a **CNAME** value (e.g. `nua-frontend-production.up.railway.app`).

### On your domain registrar (GoDaddy / Namecheap / Cloudflare):
- Add a CNAME record: `www` → `nua-frontend-production.up.railway.app`
- Add an A record for the root using Railway's IP, OR
- If your registrar supports CNAME flattening (Cloudflare does), point `@` → same target.

Wait 5–30 minutes. Railway auto-issues a free HTTPS certificate. 🔒

Then update `FRONTEND_URL` in the backend service again to your custom domain.

---

## 👥 Step 8 — Add the Crew (staff) and Pulse (owner) apps (optional)

Nua ships two extra front doors to the *same* frontend build: **NUA Crew** (a
narrow, mobile-first app for clock-in/roster/time-off) and **NUA Pulse**
(an AI-forward owner dashboard). Neither is a separate deploy — they're
routes (`/staff-app`, `/owner-dashboard`) in the app you already built in
Step 5, switched on by which hostname loaded the page
(`frontend/src/lib/appShell.js`). So this step is *only* two more custom
domains on the **same frontend service**, plus one backend variable update.

### On Railway:
1. **Frontend service → Settings → Networking → Custom Domain** → add
   `staff.nua-eatery.com` → **Add Domain**. Repeat for `owner.nua-eatery.com`.
   (Same service both times — you're adding domains #2 and #3 to the
   frontend you already have, not creating new services.)
2. Railway shows a CNAME for each — same target as your main domain's CNAME.

### On your domain registrar:
- Add a CNAME record: `staff` → *(the CNAME target Railway gave you)*
- Add a CNAME record: `owner` → *(same)*

Wait 5–30 minutes for certs, same as Step 7.

### Back on Railway — the one variable that actually makes it work:
**Backend service → Variables → `FRONTEND_URL`** — this has to list *all
three* origins, comma-separated, or the browser's CORS check silently
blocks `staff.`/`owner.` even once DNS resolves fine:

```
https://nua-eatery.com,https://staff.nua-eatery.com,https://owner.nua-eatery.com
```

Save → Railway auto-redeploys the backend (~1 minute).

### Verify:
Open `staff.nua-eatery.com` and `owner.nua-eatery.com` — each should log in
and show real data (Crew / Pulse respectively), not just the shell with
blank tiles. Blank/failing data after DNS resolves means `FRONTEND_URL`
above is missing an origin or has a typo (no trailing slash, exact scheme).

---

## 💸 Cost breakdown

| What | Free tier | Real cost |
|---|---|---|
| Railway (Hobby plan) | $5/month free credit | ~$8–15/month for a small restaurant |
| MongoDB add-on | Included in usage | counted in the $5 |
| Domain | not included | ~$12/year |

**Trial mode**: First $5 of usage is free every month. You'll burn through it in ~3 weeks of always-on usage, then it's pay-as-you-go.

---

## 🔁 Day-2 — How to update later

Every time you make a code change:

1. In Emergent chat → click **"Save to GitHub"**
2. Railway sees the git push and **auto-redeploys** within 2 minutes. No clicks needed.

That's the whole secret sauce — git push = live in production.

---

## 🩹 Troubleshooting

| Symptom | Fix |
|---|---|
| Build fails with "command not found: yarn" | In frontend service Settings → Builder, switch to **NIXPACKS** (default). It auto-installs yarn. |
| Frontend loads but every API call is `net::ERR_NAME_NOT_RESOLVED` | `REACT_APP_BACKEND_URL` wasn't set at build time. Set it, then **Deployments → Redeploy**. |
| Backend returns 502 | Check **Deployments → View Logs**. Usually a missing variable. |
| MongoDB connection refused | Make sure `MONGO_URL` was copied from the Mongo service's **Variables** tab, not a placeholder. |
| App keeps "sleeping" | Hobby plan: services sleep after idle. Upgrade to Pro ($20/mo) or set min replicas to 1. |
| "Application failed to respond" | Wrong start command. For backend it must use `$PORT` (Railway sets it dynamically). |
| Custom domain stuck "Pending" | DNS hasn't propagated. Run `dig +short www.yourdomain.com` — should return the Railway CNAME. |

---

## ✅ The "I just did it" checklist

- [ ] Code pushed to GitHub
- [ ] Railway project created
- [ ] MongoDB service added → connection string copied
- [ ] Backend service added with all 6 variables set
- [ ] Backend deployed → `/api/social/platforms` returns JSON
- [ ] Frontend service added with `REACT_APP_BACKEND_URL` set
- [ ] Frontend deployed → loads in browser
- [ ] Logged in successfully as `owner@nuva.com`
- [ ] Updated backend's `FRONTEND_URL` to the real frontend URL
- [ ] (Optional) Custom domain + HTTPS certificate
- [ ] (Optional) Crew + Pulse: `staff.` and `owner.` custom domains added to the frontend service
- [ ] (Optional) `FRONTEND_URL` updated to the comma-separated list of all three origins

---

## 🎁 Pro tips

1. **Use Railway's CLI for log tailing**: `npm i -g @railway/cli` → `railway logs --service backend` → live tail.
2. **Environment groups**: Railway lets you share variables across services. Add a shared group called "shared-secrets" so you only set `EMERGENT_LLM_KEY` once.
3. **Preview environments**: Settings → Environments → create `staging`. Every Pull Request gets its own URL automatically.
4. **Backup**: Mongo service → Settings → enable **automated backups** ($1/month).
5. **Monitor**: Built-in **Metrics** tab shows CPU, memory, request rate — no extra setup.

---

## 🆚 Quick decision tree

```
Is this your first deployment ever?
├── YES  → Use Railway (this guide). Visual, easy.
└── NO   → Want to save money long-term?
          ├── YES → Use Fly.io (/app/Fly.io Setup.md)
          └── NO  → Stick with Railway. It just works.
```

You're done. 🎉
