# Job Application Tracker — Project Context for Claude

## What we are building
A full-stack Job Application Tracker web application that helps a job seeker
log every application they submit, upload custom resumes and cover letters per
application, track status updates across the hiring pipeline, and receive email
reminders for follow-ups and scheduled interviews.

---

## Tech stack
- **Backend:** FastAPI (Python 3.11+), async SQLAlchemy + asyncpg, PostgreSQL
- **Migrations:** Alembic
- **File storage:** Local disk (uploads/ folder), S3-ready abstraction layer
- **Task queue:** Celery + Redis (scheduled email reminders)
- **Email:** SendGrid (SMTP fallback supported)
- **Frontend:** React 18, functional components + hooks, TanStack Query (React Query)
- **HTTP client:** Axios (encapsulated in services/ layer — never called directly in components)
- **Styling:** Tailwind CSS
- **Environment:** Google Antigravity (cloud IDE)

---

## Folder structure

```
job-tracker/
├── backend/
│   ├── main.py                     # FastAPI app entry, CORS, router registration
│   ├── database.py                 # Async SQLAlchemy engine + get_db dependency
│   ├── celery_worker.py            # Celery app definition + beat schedule
│   ├── models/
│   │   └── application.py         # ORM models: Application, TimelineEvent, NotificationSettings
│   ├── schemas/
│   │   └── application.py         # Pydantic v2 schemas for all request/response shapes
│   ├── routers/
│   │   ├── applications.py        # CRUD endpoints for applications
│   │   ├── files.py               # File upload + download endpoints
│   │   ├── notifications.py       # Email settings + test email endpoint
│   │   └── analytics.py           # Summary stats endpoint
│   ├── services/
│   │   ├── email_service.py       # SendGrid integration + email templates
│   │   ├── file_service.py        # Upload handling, MIME validation, storage abstraction
│   │   └── reminder_service.py    # Celery tasks: interview reminders, follow-up alerts, stale alerts
│   ├── alembic/                   # DB migrations (auto-generated)
│   ├── requirements.txt
│   └── .env                       # Secrets — never commit
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Applications.jsx
│   │   │   ├── FollowUps.jsx
│   │   │   ├── Analytics.jsx
│   │   │   └── Settings.jsx
│   │   ├── components/
│   │   │   ├── JobCard.jsx
│   │   │   ├── AddApplicationModal.jsx
│   │   │   ├── UpdateStatusModal.jsx
│   │   │   ├── DetailPanel.jsx
│   │   │   ├── Timeline.jsx
│   │   │   ├── FileUploadZone.jsx
│   │   │   └── StatCard.jsx
│   │   ├── services/
│   │   │   ├── api.js               # Axios instance with base URL + interceptors
│   │   │   ├── applicationService.js
│   │   │   └── fileService.js
│   │   ├── hooks/
│   │   │   └── useApplications.js   # TanStack Query hooks
│   │   └── App.jsx                  # Router + layout
│   ├── .env                         # VITE_API_BASE_URL
│   └── package.json
├── docker-compose.yml               # PostgreSQL + Redis
└── README.md
```

---

## Database schema

### Table: applications
| Column           | Type      | Notes                                              |
|------------------|-----------|----------------------------------------------------|
| id               | UUID (PK) | auto-generated                                     |
| job_title        | VARCHAR   | required                                           |
| company          | VARCHAR   | required                                           |
| date_applied     | DATE      | required                                           |
| source           | VARCHAR   | LinkedIn / Indeed / Glassdoor / Company site / etc |
| location         | VARCHAR   | nullable                                           |
| salary_range     | VARCHAR   | nullable                                           |
| job_description  | TEXT      | nullable — paste of JD                             |
| notes            | TEXT      | nullable — recruiter contact, referral info        |
| status           | ENUM      | applied / interview / followup / offer / rejected  |
| resume_path      | VARCHAR   | file path or S3 key — nullable                     |
| cover_path       | VARCHAR   | nullable                                           |
| created_at       | TIMESTAMP | auto                                               |
| updated_at       | TIMESTAMP | auto                                               |

### Table: timeline_events
| Column           | Type      | Notes                                              |
|------------------|-----------|----------------------------------------------------|
| id               | UUID (PK) |                                                    |
| application_id   | UUID (FK) | → applications.id (cascade delete)                |
| event_date       | DATE      | date of this status change                         |
| status           | ENUM      | same values as applications.status                 |
| note             | TEXT      | nullable — what happened, recruiter feedback       |
| interview_date   | DATE      | nullable — set when status = interview             |
| interview_type   | VARCHAR   | nullable — phone / technical / panel / final       |
| interviewer      | VARCHAR   | nullable — name, title, contact                    |
| created_at       | TIMESTAMP | auto                                               |

### Table: notification_settings
| Column             | Type     | Notes                                            |
|--------------------|----------|--------------------------------------------------|
| id                 | UUID (PK)|                                                  |
| email              | VARCHAR  | user's notification email                        |
| notify_interview   | BOOLEAN  | default true — 24h before interview              |
| notify_followup    | BOOLEAN  | default true — when follow-up is due             |
| notify_stale       | BOOLEAN  | default true — 7+ days with no update            |
| weekly_summary     | BOOLEAN  | default false — Monday digest                    |
| followup_freq_days | INTEGER  | days between follow-ups, default 7               |

---

## API endpoints

### Applications
```
GET    /api/applications             list all; supports ?status=&search= query params
POST   /api/applications             create new application
GET    /api/applications/{id}        get single application with full timeline
PATCH  /api/applications/{id}        update status + append timeline event
DELETE /api/applications/{id}        hard delete application and its files
```

### Files
```
POST   /api/files/upload             multipart/form-data; returns { filename, path }
GET    /api/files/{filename}         serve file as download
```

### Notifications
```
GET    /api/notifications/settings   get current notification preferences
PUT    /api/notifications/settings   save preferences
POST   /api/notifications/test       send a test email to the configured address
```

### Analytics
```
GET    /api/analytics/summary        returns:
                                       - count by status
                                       - interview conversion rate
                                       - applications this month
                                       - top 5 companies applied to
                                       - average days to first response
```

---

## Email notification rules (Celery tasks)

| Trigger | When | Task name |
|---------|------|-----------|
| Interview reminder | 24h before `interview_date` | `send_interview_reminder` |
| Follow-up due | `(today - date_applied) % followup_freq_days == 0` and status is applied or followup | `send_followup_reminder` |
| Stale application | 7+ days since last timeline event and status = applied | `send_stale_alert` |
| Weekly summary | Every Monday 08:00 | `send_weekly_summary` |

Celery beat runs on a schedule. All tasks read notification_settings before sending.
If `notify_*` is false for that alert type, skip silently.

---

## Code standards — Claude must follow these at all times

### Backend rules
- Use **Pydantic v2** models for all request/response validation
- All DB operations must be **async** (`async def` + `await`)
- Use `Depends(get_db)` for all database session injection — never create sessions manually
- Return correct HTTP status codes: 201 for create, 200 for update/get, 204 for delete, 404 for not found
- Use `HTTPException` for all error responses with a human-readable `detail` message
- File uploads: validate MIME type (only PDF and DOCX allowed), enforce 5 MB max per file
- Never hardcode secrets — always read from `os.environ` via `python-dotenv`
- Prefix all API routers with `/api`
- Every file must include its path as a comment on line 1: `# backend/routers/applications.py`

### Frontend rules
- All components must be **functional with hooks** — no class components
- Every component that fetches data must handle three states: **loading**, **error**, **empty**
- All API calls go through `services/` — never import axios directly in a component
- Use **TanStack Query** for all server state (fetching, caching, invalidation)
- Forms use **controlled inputs** with `useState` — never uncontrolled refs
- File uploads use `<input type="file">` inside a styled drop zone, sent as `FormData` via `fileService.js`
- Every file must include its path as a comment on line 1: `// frontend/src/components/JobCard.jsx`

### General rules
- `.env` files are never committed — add them to `.gitignore` immediately when scaffolding
- When a feature can fail in production (null file path, missing interview date, duplicate entry),
  add a `# WARN:` comment and handle the error explicitly — do not silently ignore it
- When multiple approaches exist, pick one, implement it fully, and note the trade-off in a comment
- Never use `print()` for debugging in production code — use Python's `logging` module

---

## Environment variables

### backend/.env
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/jobtracker
REDIS_URL=redis://localhost:6379/0
SENDGRID_API_KEY=your_sendgrid_key_here
FROM_EMAIL=noreply@jobtracker.app
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=5
```

### frontend/.env
```
VITE_API_BASE_URL=http://localhost:8000
```

---

## How to start the project in Antigravity

```bash
# Step 1 — start services
docker-compose up -d

# Step 2 — backend setup
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000

# Step 3 — start Celery (open a second terminal)
celery -A celery_worker worker --beat --loglevel=info

# Step 4 — frontend setup (open a third terminal)
cd frontend
npm install
npm run dev
```

---

## Build order — follow this sequence exactly

When I ask Claude Code to build something, it should follow this order:

1. `docker-compose.yml` — PostgreSQL + Redis services
2. `backend/database.py` — async engine, session factory, get_db dependency
3. `backend/models/application.py` — all three ORM models
4. Alembic migration — `alembic init` + first migration for all tables
5. `backend/schemas/application.py` — all Pydantic v2 schemas
6. `backend/routers/applications.py` — full CRUD
7. `backend/services/file_service.py` + `backend/routers/files.py`
8. `backend/services/email_service.py` + `backend/routers/notifications.py`
9. `backend/services/reminder_service.py` + `backend/celery_worker.py`
10. `backend/routers/analytics.py`
11. `backend/main.py` — wire everything together
12. `frontend/src/services/api.js` + `applicationService.js` + `fileService.js`
13. `frontend/src/hooks/useApplications.js`
14. `frontend/src/pages/Dashboard.jsx` + `Applications.jsx`
15. `frontend/src/components/` — all modal and card components
16. `frontend/src/pages/FollowUps.jsx` + `Analytics.jsx` + `Settings.jsx`
17. `frontend/src/App.jsx` — routing + layout

---

## Status values (use these exact strings everywhere — DB, API, frontend)
```
applied     → just submitted the application
interview   → interview has been scheduled
followup    → follow-up email has been sent
offer       → offer received
rejected    → application rejected
```
