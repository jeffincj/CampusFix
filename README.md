# CampusFix

AI complaint system for a college campus. Students report problems (hostel, mess,
Wi-Fi, lab, transport, ...) in English, Tamil, Malayalam or mixed language; AI
routes them to the right department. Staff and admins work from a dashboard.

> Status: **Phase 3 done**. Phase 1: project setup, Docker + MySQL, custom user with
> roles, register/login. Phase 2: complaint models, CRUD pages, status workflow with
> history, live status refresh, feedback, Django admin, 8 seeded departments.
> Phase 3: REST API (Django REST Framework) with JWT login and role permissions. The full README (architecture diagram, retraining,
> Render deployment, "what I would improve") is written in Phase 8.

## Folder layout (so far)

```
backend/
  manage.py
  config/      settings (read from .env), urls, settings_test (SQLite for pytest)
  accounts/    custom User model with role (student/staff/admin) + department (table: users)
  complaints/  models (departments, complaints, complaint_status_history, duplicate_links,
               feedback), services.py (business rules), admin, department seed data
  web/         Django templates + static CSS/JS (forms.js validation, status.js live refresh)
  tests/       pytest tests
frontend/      React dashboard (Phase 7)
docker-compose.yml   MySQL 8 + Django backend
.env.example         copy to .env; no secrets are hard-coded
```

## Run with Docker (recommended)

```bash
cp .env.example .env          # then edit the passwords and secret key
docker compose up --build     # starts MySQL, runs migrations, serves on :8000
docker compose exec backend python manage.py createsuperuser   # creates an admin
```

Open http://localhost:8000. Admin panel: http://localhost:8000/admin/

## Run locally without Docker

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env          # set DB_ENGINE=sqlite for a quick try without MySQL
cd backend
python manage.py migrate
python manage.py runserver
```

## Roles

| Role    | How it is created                          | Can do (grows each phase)            |
|---------|--------------------------------------------|---------------------------------------|
| student | self-registration on `/register/`          | submit and track own complaints       |
| staff   | admin sets role in Django admin            | see/update own department's complaints|
| admin   | `createsuperuser` (always gets role admin) | everything                            |

The registration form has no role field, so a student can never sign up as staff or admin.
To create a staff user: Django admin → Users → add user → set role "Staff" and a department
(staff without a department is rejected).

## Complaint workflow

```
open ──► in_progress ──► resolved ──► closed
 │  └──────────────────►    │
 │            ▲             │ (reopen if the fix did not work)
 │            └─────────────┘
 └──► rejected                       in_progress ──► open is also allowed
```

Every change writes a row to `complaint_status_history` (who, when, note). The rules live in
`complaints/services.py`, used by the HTML pages, the Django admin and (Phase 3) the API.

| Page                        | Who                         |
|-----------------------------|-----------------------------|
| `/complaints/new/`          | students                    |
| `/complaints/`              | everyone (own / department / all) |
| `/complaints/<id>/edit/`, `/delete/` | owner, only while status is open |
| status update form          | staff of that department, admins |
| feedback (1–5 stars)        | owner, once, after resolved |

Departments (seeded by a data migration, refresh with `python manage.py seed_departments`):
Hostel, Mess & Food, IT (Wi-Fi), Labs & Academics, Transport, Maintenance (Electrical &
Plumbing), Housekeeping & Sanitation, Security.

## REST API (JWT)

Log in to get tokens, then send `Authorization: Bearer <access>` on every request.
Access tokens last 30 minutes; use the refresh token to get a new one (both set in `.env`).

```bash
curl -X POST localhost:8000/api/auth/login/ -H 'Content-Type: application/json' \
     -d '{"username": "warden", "password": "..."}'
# -> {"access": "...", "refresh": "...", "user": {"role": "staff", ...}}
curl localhost:8000/api/complaints/?status=open -H "Authorization: Bearer <access>"
```

| Method & path                     | Who                  | Notes |
|-----------------------------------|----------------------|-------|
| `POST /api/auth/register/`        | anyone               | always creates a **student**; rate-limited |
| `POST /api/auth/login/`           | anyone               | returns `access`, `refresh`, `user`; token carries `role`; rate-limited |
| `POST /api/auth/refresh/`         | anyone with refresh  | new access token |
| `GET /api/auth/me/`               | logged in            | current user |
| `GET /api/departments/`           | logged in            | 8 departments |
| `GET /api/complaints/`            | logged in            | student: own · staff: own department · admin: all. Filters: `status, category, urgency, department, block, needs_review, q, from, to (YYYY-MM-DD), ordering`; 20 per page |
| `POST /api/complaints/`           | student              | `title, description, category?, location?, block?` |
| `GET /api/complaints/{id}/`       | if visible           | includes status `history`; invisible → 404 |
| `PATCH /api/complaints/{id}/`     | by role              | student (own, while open): `title, description, location, block, category` · staff (own dept): `status, note, urgency` · admin: staff fields + `category, needs_review`. Other fields → 403; bad status move → 400 |
| `GET /api/complaints/stats/`      | staff, admin         | `total, by_category, by_status, by_urgency, by_block, by_week` (`?weeks=12`) |

No PUT or DELETE on complaints. Endpoints for hotspots, spikes, AI, chat, documents,
metrics and reports come in later phases.

## Tests

```bash
cd backend
pytest -q        # uses in-memory SQLite (config/settings_test.py), no MySQL needed
```
