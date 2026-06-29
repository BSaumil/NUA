# Auto-Deploy via GitHub Actions

Every time you push code to `main`, GitHub will automatically deploy it to Fly.io. No CLI, no commands, no clicks. Just commit and walk away.

---

## 🔧 One-time setup (5 minutes)

### 1. Create a Fly.io API token

On your computer:
```bash
flyctl auth token
```
Copy the long string it prints (starts with `fo1_...`).

> 🔒 This token grants deploy rights. Treat it like a password.

### 2. Add the token to your GitHub repo

1. Go to your repo on GitHub.
2. Click **Settings → Secrets and variables → Actions → New repository secret**.
3. Name: `FLY_API_TOKEN`
4. Secret: *paste the token from step 1*
5. Click **Add secret**.

### 3. Push the workflow file

The file is already in your repo at `.github/workflows/deploy.yml`. Just push it:

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: auto-deploy to Fly on push to main"
git push
```

Done. From now on, **every push to `main` deploys automatically**.

---

## 🎯 How it works

```
You push code to main
        │
        ▼
GitHub detects which folder changed (backend/ or frontend/)
        │
        ▼
Deploys ONLY the affected service (skips unchanged ones)
        │
        ▼
Smoke tests the deployed URL
        │
        ▼
Posts a result summary in the Actions tab ✅
```

- **Backend change only** → backend redeploys, frontend stays put (~2 min total)
- **Frontend change only** → frontend redeploys, backend stays put (~3 min)
- **Both changed** → backend deploys first, then frontend (~5 min, in order)
- **Docs/.md changes only** → no deploy (waste of CI minutes)

---

## 🎮 Manual deploy

Don't want to push code but need to force a redeploy?

1. GitHub → your repo → **Actions** tab
2. Click **"Deploy to Fly.io"** in the left sidebar
3. Click **"Run workflow"** dropdown on the right
4. Choose target: `both` / `backend` / `frontend`
5. Click the green **Run workflow** button

---

## 🩹 Troubleshooting

| Symptom | Fix |
|---|---|
| Workflow says "FLY_API_TOKEN: not set" | Re-do step 2. Spelling matters. |
| `Error: this token doesn't have access to app` | Token was scoped to one app. Regenerate: `flyctl tokens create deploy` |
| Deploy succeeds but smoke test fails | Fly is still spinning up the new VM. Click "Re-run jobs" in Actions tab. |
| Both jobs always run even on docs-only change | Check the `paths:` block in deploy.yml — should include `backend/**`, `frontend/**` only. |
| Want to skip a deploy for a tiny commit | Add `[skip ci]` to your commit message. |

---

## 🔐 Security notes

- The `FLY_API_TOKEN` secret is encrypted at rest and only injected at runtime.
- Pull requests from forks **cannot** access secrets (GitHub's default — keeps you safe).
- Rotate the token every 90 days: `flyctl tokens revoke <id>` → re-create → update GitHub secret.

---

## 🎁 Optional upgrades

### Add Slack notifications

In `.github/workflows/deploy.yml`, replace the `notify` job with:

```yaml
  notify:
    needs: [deploy-backend, deploy-frontend]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Slack ping
        uses: slackapi/slack-github-action@v1.27.0
        with:
          payload: |
            {
              "text": "🚀 Nua deployed: backend=${{ needs.deploy-backend.result }}, frontend=${{ needs.deploy-frontend.result }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

Add `SLACK_WEBHOOK_URL` to your repo secrets (get the URL from https://api.slack.com/messaging/webhooks).

### Add a staging environment

Create a `staging` branch + a second Fly app (`nua-backend-staging`, `nua-frontend-staging`). Duplicate the workflow with branch filters — every PR gets its own preview URL.

---

You're done. **Push code → app updates. That's the dream.** 🎉
