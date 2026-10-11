# CampusFix

AI complaint system for a college campus. Students report problems (hostel, mess,
Wi-Fi, lab, transport, ...) in English, Tamil, Malayalam or mixed language; AI
routes them to the right department. Staff and admins work from a dashboard.

> Status: **Phase 1 done** (project setup, Docker + MySQL, custom user with roles,
> student register/login pages). The full README (architecture diagram, retraining,
> Render deployment, "what I would improve") is written in Phase 8.

## Folder layout (so far)

```
backend/
  manage.py
  config/      settings (read from .env), urls, settings_test (SQLite for pytest)
  accounts/    custom User model with role: student / staff / admin  (table: users)
  web/         Django templates + static CSS/JS for student pages
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

## Tests

```bash
cd backend
pytest -q        # uses in-memory SQLite (config/settings_test.py), no MySQL needed
```
