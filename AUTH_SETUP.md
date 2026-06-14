# Auth setup — what you need to do in dashboards

The code is in place. To actually use signin/signup you need to wire up
Supabase Auth and pass the right secrets to Render + GitHub Pages.

## 1. Supabase dashboard

Go to https://supabase.com/dashboard → your project.

### Settings → API
Copy these values, you'll need them in steps 2 and 3:
- **Project URL** (e.g. `https://abcdefg.supabase.co`)
- **anon public key** (safe to ship to the browser)
- **JWT Secret** (Settings → JWT Settings → JWT Secret — **server-side only**, never ship to browser)

### Authentication → Providers → Email
- Enable email provider
- Decide whether you want "Confirm email" on (recommended) or off (faster testing)

### Authentication → Providers → Google
- Enable Google provider
- You'll need a Google Cloud OAuth client ID + secret:
  1. https://console.cloud.google.com/apis/credentials → Create Credentials → OAuth client ID → Web app
  2. **Authorized JavaScript origins**: add `https://sandeepkumaramgothu.github.io`
  3. **Authorized redirect URIs**: add `https://YOUR_PROJECT.supabase.co/auth/v1/callback`
  4. Copy the Client ID + Secret, paste them into Supabase's Google provider config
- Save

### Authentication → URL Configuration
- **Site URL**: `https://sandeepkumaramgothu.github.io/Job_Tracker/`
- **Redirect URLs** (one per line):
  ```
  https://sandeepkumaramgothu.github.io/Job_Tracker/
  http://localhost:5173/
  ```

## 2. Render (backend) env vars

Render dashboard → your `jobtracker-api` service → Environment, add:
- `SUPABASE_JWT_SECRET` = the JWT Secret from step 1
- `SUPABASE_JWT_AUDIENCE` = `authenticated` (default; only change if you renamed it)

Render will auto-redeploy after saving.

## 3. GitHub Pages (frontend) build vars

GitHub repo → Settings → Secrets and variables → **Actions** → **Variables** tab → New repository variable:
- `VITE_SUPABASE_URL` = your Project URL from step 1
- `VITE_SUPABASE_ANON_KEY` = your anon public key from step 1

(You should already have `VITE_API_BASE_URL` here.)

Then trigger a redeploy: Actions → "Deploy Frontend to GitHub Pages" → Run workflow.

## 4. Local development env

Update `backend/.env` (already templated, fill in real values):
```
SUPABASE_JWT_SECRET=...   # JWT Secret from step 1
SUPABASE_JWT_AUDIENCE=authenticated
```

Update `frontend/.env`:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=...
```

## 5. Database migration

The new migration adds `user_id` to `applications` and `notification_settings`
and **deletes any existing rows** (your single test application). After Render
redeploys, the build command runs `alembic upgrade head` automatically and the
schema updates. If you ever want to keep existing data, edit the
`8a1c4f2d9b7e_add_user_id_for_supabase_auth.py` migration before deploying.

## What the user experience looks like

- Land on the site → see Login screen
- Sign up with email/password → confirmation email (if enabled) → click link → sign in
- Or click "Continue with Google" → Google consent → redirected back, signed in
- Every API request now carries `Authorization: Bearer <jwt>`
- Settings page has a "Sign out" button at the bottom
- Each user only sees their own applications, files, analytics, notifications
