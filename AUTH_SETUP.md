# Auth setup — step by step (current Supabase UI, June 2026)

Do this once. ~30 minutes. Four places to visit: Supabase, Google Cloud,
Render, and your GitHub repo's Actions settings.

Your specific values (from your dashboard screenshot):
- Project ref: `csmvpeidkkexbeaglwoe`
- Project URL: `https://csmvpeidkkexbeaglwoe.supabase.co`

---

## PART A — Collect three values from Supabase

The Supabase sidebar has two layers. The outer dark strip on the far left
has icons (Home, Table Editor, SQL Editor, **Authentication** 🔐, Storage,
Edge Functions, Realtime, Advisors, Reports, Logs, **Project Settings** ⚙️).
Project Settings is the gear icon near the bottom. Clicking it shows the
second sidebar you've already been seeing: General, Compute and Disk,
Infrastructure, Integrations, **API Keys**, **JWT Keys**, Log Drains,
Add-ons.

### A1. **Project URL** — `https://csmvpeidkkexbeaglwoe.supabase.co`

You already have it from the General settings page (Project ID =
`csmvpeidkkexbeaglwoe`, so the URL is `https://<project-id>.supabase.co`).
No copy needed; just keep it handy.

### A2. **Anon (publishable) key** — long string starting with `eyJ…`

1. Sidebar → **Project Settings** (gear icon) → **API Keys**.
2. You'll see a list of keys. Copy the row labeled **`anon`** /
   **`public`** / **"Publishable key"** (different wording in different
   project ages — they're all the same key).
3. **Do not** copy the `service_role` / "secret" row. That one bypasses
   security and must never reach the browser.

### A3. **JWT Secret** — long random string, server-side only

1. Sidebar → **Project Settings → JWT Keys**.
2. On this page you'll see two things:
   - A "Signing keys" section showing a public/private key pair (asymmetric).
   - A **"Legacy JWT Secret"** or **"JWT Secret"** section showing one long
     HS256 string with a Copy button.
3. Copy the **legacy / HS256** secret. (The backend code uses HS256 to
   verify tokens. If Supabase only shows the new asymmetric keys and no
   legacy secret, look for a toggle that says *"Enable legacy JWT secret"*
   or *"Reveal legacy secret"* and click it.)

Stash these three values somewhere safe — you'll paste them into Render
(A3) and GitHub (A1 + A2) shortly.

---

## PART B — Enable Email sign-in

1. Outer sidebar → **Authentication** icon (🔐, the lock — *not* the gear).
2. Inside Authentication, find the **Sign In / Providers** sub-page. In the
   current UI this is under the left-rail header "Configuration":
   - Look for **Sign In / Up** or **Providers** in the inner sidebar.
   - You may see them grouped under "Auth Providers".
3. Click into **Email**.
4. Toggle **"Enable Email provider"** to ON.
5. Decide on **"Confirm email"**:
   - **ON (recommended)** — new users get a confirmation email first.
   - **OFF** — instant signup, no inbox round-trip. Easier for first tests;
     flip on before sharing the app.
6. Click **Save**.

---

## PART C — Enable Google sign-in

Google OAuth = two halves. You create credentials in Google Cloud and paste
them into Supabase.

### C1. Create the OAuth client in Google Cloud

1. Open https://console.cloud.google.com/apis/credentials.
2. Top bar → project picker → create a new project (any name like
   `Job Tracker`) if you don't have one. Wait for it to finish.
3. **First-time setup only**: Google requires you to configure the OAuth
   consent screen before issuing credentials.
   - Left sidebar → **APIs & Services → OAuth consent screen**.
   - User Type: **External** → Create.
   - App name: `Job Tracker`. User support email: your email.
   - Developer contact: your email.
   - Save and Continue through "Scopes" (default) and "Test users" (add
     your own Gmail).
   - Back to dashboard.
4. Sidebar → **APIs & Services → Credentials**.
5. **Create Credentials** → **OAuth client ID**.
6. Application type: **Web application**.
7. Name: `Job Tracker — Supabase`.
8. **Authorized JavaScript origins** — click *Add URI* for each:
   ```
   https://sandeepkumaramgothu.github.io
   http://localhost:5173
   ```
9. **Authorized redirect URIs** — click *Add URI*:
   ```
   https://csmvpeidkkexbeaglwoe.supabase.co/auth/v1/callback
   ```
10. **Create**. A modal shows your **Client ID** and **Client Secret** —
    copy both. (You can re-open them later from the credentials page.)

### C2. Paste them into Supabase

1. Back to Supabase → **Authentication → Sign In / Providers**.
2. Click into **Google**.
3. Toggle **Enable**.
4. **Client ID (for OAuth)** — paste the Google Client ID from C1.
5. **Client Secret (for OAuth)** — paste the Google Client Secret from C1.
6. Leave **Authorized Client IDs** blank.
7. Click **Save**.

---

## PART D — Site URL and Redirect URLs in Supabase

This tells Supabase which addresses are allowed to receive confirmation
links and the OAuth callback. Without this, sign-in succeeds but the
redirect at the end drops the user on the wrong page.

1. Outer sidebar → **Authentication** (🔐).
2. Inner sidebar → **URL Configuration** (sometimes under "Configuration"
   → "URL Configuration"). If you can't find it, try the URL
   `https://supabase.com/dashboard/project/csmvpeidkkexbeaglwoe/auth/url-configuration`.
3. **Site URL** — set to exactly:
   ```
   https://sandeepkumaramgothu.github.io/Job_Tracker/
   ```
4. **Redirect URLs** — there's an *Add URL* button. Add each of these as
   separate entries:
   ```
   https://sandeepkumaramgothu.github.io/Job_Tracker/
   https://sandeepkumaramgothu.github.io/Job_Tracker/**
   http://localhost:5173/
   http://localhost:5173/**
   ```
   The `/**` versions let Supabase redirect to *any* sub-route after OAuth.
5. **Save**.

---

## PART E — Backend env vars on Render

1. https://dashboard.render.com → your `jobtracker-api` service.
2. Left sidebar → **Environment**.
3. **Add Environment Variable** twice:

   | Key | Value |
   | --- | --- |
   | `SUPABASE_JWT_SECRET` | the JWT Secret from A3 |
   | `SUPABASE_JWT_AUDIENCE` | `authenticated` |

4. **Save Changes**. Render auto-redeploys. The build script runs
   `alembic upgrade head`, which adds the `user_id` columns. Give it ~2
   minutes.

> Heads-up: that migration **deletes the existing applications and
> notification_settings rows** (the one Virginia Tech test entry). Pre-auth
> rows have no owner in the new multi-tenant model. Recreate after sign-in.

---

## PART F — Frontend build vars on GitHub

The frontend bundle is built by a GitHub Action. It needs Supabase
credentials baked in at build time.

1. GitHub repo → **Settings** tab (top of repo page).
2. Left sidebar → **Secrets and variables** → **Actions**.
3. Click the **Variables** tab (not "Secrets" — the workflow uses
   `vars.*`).
4. **New repository variable** twice:

   | Name | Value |
   | --- | --- |
   | `VITE_SUPABASE_URL` | `https://csmvpeidkkexbeaglwoe.supabase.co` |
   | `VITE_SUPABASE_ANON_KEY` | the anon key from A2 |

5. Trigger a redeploy: **Actions** tab → **"Deploy Frontend to GitHub
   Pages"** → **Run workflow** → branch `main` → **Run workflow**.

Workflow finishes in ~1 minute. The deployed bundle now has the Supabase
client wired up.

---

## PART G — (Optional) Local development

Skip unless you'll run the app on your laptop.

`backend/.env`:
```
SUPABASE_JWT_SECRET=<paste A3>
SUPABASE_JWT_AUDIENCE=authenticated
```

`frontend/.env`:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://csmvpeidkkexbeaglwoe.supabase.co
VITE_SUPABASE_ANON_KEY=<paste A2>
```

Restart `uvicorn` and `npm run dev` after editing.

---

## PART H — Smoke-test the deployed app

1. Open `https://sandeepkumaramgothu.github.io/Job_Tracker/`.
2. You should see the **Login** screen.
3. **Sign Up** tab → enter email + password → **Create account**.
4. If email confirmation is on, open the link from your inbox, then come
   back and **Sign In**.
5. Or: **Continue with Google** → pick your Google account → consent → you
   land back on the dashboard, signed in.
6. Dashboard shows zero applications (expected — the migration cleared the
   pre-auth row). Add one to confirm the API works end-to-end.
7. Settings → bottom "Account" card shows your email + Sign out button.

---

## Troubleshooting

| Symptom | Most likely cause | Fix |
| --- | --- | --- |
| Login page is blank or "VITE_SUPABASE_URL missing" in browser console | GitHub Actions vars weren't set when the bundle was built | Set the two vars in **Part F**, then re-run the Deploy workflow |
| Every API call returns 401 immediately after signing in | Backend `SUPABASE_JWT_SECRET` wrong or audience mismatch | Re-copy from **Part A3**, update on Render, wait for redeploy |
| Google login → "redirect_uri_mismatch" | Google Cloud OAuth client missing Supabase callback URI | In Google Cloud Credentials, add `https://csmvpeidkkexbeaglwoe.supabase.co/auth/v1/callback` to Authorized redirect URIs |
| Confirmation email never arrives | Spam folder, or "Confirm email" toggle off (the link won't be sent at all) | Check spam. Or toggle off in **Part B** for instant signup |
| Email confirmation link lands on `localhost` instead of GitHub Pages | Site URL not set | **Part D** — set Site URL to the GitHub Pages URL |
| Signed in then immediately bounced back to Login | axios's 401-handler triggers signOut. Almost always wrong JWT secret on Render | Re-check **Part E** |
| Backend logs `Rejected token: Invalid audience` | `SUPABASE_JWT_AUDIENCE` env var is wrong | Should be `authenticated` |
| "Cannot create an application directly in 'interview' status" | Not auth-related — that's the validation I added last commit | Create the application as `applied` first, then update status |
