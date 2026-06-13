# Job Application Tracker

A full-stack web application to log every job application you submit, track status updates across the hiring pipeline, upload custom resumes and cover letters, and receive automated email reminders for follow-ups and scheduled interviews.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11+), async SQLAlchemy + asyncpg |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Task queue | Celery + Redis |
| Email | SendGrid (SMTP fallback) |
| Frontend | React 18, TanStack Query, Tailwind CSS |
| HTTP client | Axios (via services layer) |

---

## Quick Start

### Prerequisites
- Docker (for PostgreSQL + Redis)
- Python 3.9+ with pip
- Node.js 18+

### 1. Start infrastructure

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
pip3 install -r requirements.txt
cp .env.example .env        # edit with your real values
alembic upgrade head
uvicorn main:app --reload --port 8000
```

### 3. Celery worker (optional — needed for email reminders)

Open a second terminal:

```bash
cd backend
celery -A celery_worker worker --beat --loglevel=info
```

### 4. Frontend

Open a third terminal:

```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173** — the API docs are at **http://localhost:8000/docs**.

---

## Environment Variables

### `backend/.env`

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/jobtracker
REDIS_URL=redis://localhost:6379/0
SENDGRID_API_KEY=your_sendgrid_key_here
FROM_EMAIL=noreply@jobtracker.app
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=5
```

### `frontend/.env`

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## API Reference

| Method | Route | Description |
|---|---|---|
| GET | `/api/applications` | List all; `?status=` + `?search=` filters |
| POST | `/api/applications` | Create application |
| GET | `/api/applications/{id}` | Get detail + timeline |
| PATCH | `/api/applications/{id}` | Update fields + append timeline event |
| DELETE | `/api/applications/{id}` | Hard delete |
| POST | `/api/files/upload` | Upload resume/cover letter (PDF/DOCX ≤5 MB) |
| GET | `/api/files/{filename}` | Download stored file |
| GET | `/api/notifications/settings` | Get notification preferences |
| PUT | `/api/notifications/settings` | Save preferences |
| POST | `/api/notifications/test` | Send test email |
| GET | `/api/analytics/summary` | Aggregated stats |
| GET | `/health` | Readiness probe |

Full interactive docs: **http://localhost:8000/docs**

---

## Application Statuses

| Status | Meaning |
|---|---|
| `applied` | Application submitted |
| `interview` | Interview scheduled |
| `followup` | Follow-up email sent |
| `offer` | Offer received |
| `rejected` | Application rejected |

---

## Scheduled Email Reminders (Celery Beat)

| Task | Schedule | Condition |
|---|---|---|
| Interview reminder | Daily 08:00 UTC | 24h before `interview_date` |
| Follow-up reminder | Daily 09:00 UTC | `(today − date_applied) % followup_freq_days == 0` |
| Stale alert | Daily 09:30 UTC | 7+ days since last timeline event, status = `applied` |
| Weekly summary | Monday 08:00 UTC | Always (if `weekly_summary` is enabled) |

Configure notification preferences at **Settings → Notification Email**.

---

## Project Structure

```
.
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── database.py              # Async engine + get_db
│   ├── celery_worker.py         # Celery app + beat schedule
│   ├── models/application.py   # ORM models
│   ├── schemas/application.py  # Pydantic v2 schemas
│   ├── routers/                 # API routers (applications, files, notifications, analytics)
│   ├── services/                # email, file, reminder services
│   ├── alembic/                 # DB migrations
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/               # Dashboard, Applications, FollowUps, Analytics, Settings
│       ├── components/          # JobCard, DetailPanel, modals, Timeline, FileUploadZone
│       ├── hooks/               # TanStack Query hooks
│       └── services/            # api.js, applicationService.js, fileService.js
├── docker-compose.yml
└── README.md
```

---

## File Uploads

- Accepted: **PDF** and **DOCX** only
- Maximum size: **5 MB** per file
- Files are stored in `backend/uploads/` (S3-ready abstraction — swap `save_file` / `delete_file` in `services/file_service.py`)

---

## Development Notes

- Never commit `.env` files — they are in `.gitignore`
- Run `alembic revision --autogenerate -m "description"` after changing ORM models (requires PostgreSQL to be running)
- Use `alembic upgrade head` to apply pending migrations
- The Celery beat scheduler requires Redis to be running
- All backend DB operations are `async` — never create SQLAlchemy sessions manually
