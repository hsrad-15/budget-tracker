# Budget & Expense Tracker

A production-ready Django budget/expense tracker: dashboard with charts, full
transaction CRUD, on-demand PDF reports, and automated weekly/monthly PDF
report emails via Celery.

## Tech Stack
- Python 3.12, Django 5.1
- SQLite (dev) / PostgreSQL (prod)
- Bootstrap 5 + Chart.js
- WeasyPrint (PDF generation)
- Celery + Redis + django-celery-beat (scheduled emails)

## 1. Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit .env with your own values

python manage.py migrate
python manage.py createsuperuser
python manage.py shell < seed_categories.py   # optional: adds starter categories
python manage.py runserver
```

Visit http://127.0.0.1:8000/accounts/signup/ to create an account, then
http://127.0.0.1:8000/ for the dashboard.

### WeasyPrint system dependencies
WeasyPrint needs Pango/Cairo installed at the OS level.
- Ubuntu/Debian: `sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev`
- macOS: `brew install pango`
See https://doc.courtbouillon.org/weasyprint/stable/first_steps.html for other platforms.

## 2. Switching to PostgreSQL (production)

In `.env`:
```
DB_ENGINE=postgres
DB_NAME=budgetdb
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
```
Then `pip install psycopg2-binary` (already in requirements.txt) and re-run `migrate`.

## 3. Running the background email scheduler

Requires Redis running locally (or point `CELERY_BROKER_URL` at a hosted instance).

```bash
redis-server                                     # terminal 1
celery -A budgetproject worker -l info           # terminal 2
celery -A budgetproject beat -l info             # terminal 3
```

- `worker` executes tasks (sends the actual emails).
- `beat` triggers `send_weekly_reports` every Sunday at 00:00, and
  `send_monthly_reports` on the 1st of each month at 00:00 (see
  `budgetproject/celery.py` for the schedule).

To test a report email immediately without waiting for the schedule:
```bash
python manage.py shell -c "
from core.tasks import send_weekly_report_for_user
from accounts.models import User
send_weekly_report_for_user(User.objects.first().id)
"
```
With the default console `EMAIL_BACKEND`, the email (with base64 PDF
attachment) prints straight to your terminal — switch `EMAIL_BACKEND` in
`.env` to the SMTP backend for real delivery.

## 4. Project layout

```
budgetproject/
├── accounts/            # Custom User model (email login), signup/login views
├── core/                 # Category & Transaction models, dashboard, CRUD,
│   ├── models.py         # PDF views, utils.py (shared stats), tasks.py (Celery)
│   ├── forms.py
│   ├── views.py
│   ├── utils.py          # compute_period_stats(), date-range helpers
│   ├── tasks.py           # Celery tasks: weekly/monthly report emails
│   └── urls.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── registration/     # login.html, signup.html
│   ├── transactions/     # list, form, delete confirm
│   ├── reports/          # pdf_base.html, pdf_weekly.html, pdf_monthly.html
│   └── emails/           # weekly_email.html, monthly_email.html
├── static/css/style.css
├── budgetproject/
│   ├── settings.py
│   ├── urls.py
│   └── celery.py         # Celery app + beat schedule
├── seed_categories.py
├── requirements.txt
└── .env.example
```

## 5. Deployment

The project is Docker-ready — the `Dockerfile` bakes in WeasyPrint's system
dependencies (Pango/Cairo/GDK-Pixbuf), which is the #1 thing that breaks PDF
generation on plain (non-Docker) hosts. Docker is the recommended deploy path.

### 5.1 Deploy anywhere with Docker Compose (VPS / DigitalOcean / EC2 / etc.)

```bash
cp .env.example .env
# Edit .env: set a real SECRET_KEY, DEBUG=False, ALLOWED_HOSTS=yourdomain.com,
# EMAIL_* for SMTP, and CSRF_TRUSTED_ORIGINS=https://yourdomain.com

docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell < seed_categories.py
```

This brings up 5 containers: `web` (Gunicorn), `worker` (Celery), `beat`
(Celery scheduler), `db` (PostgreSQL), and `redis` — all networked together,
with migrations run automatically on `web` startup via `docker-entrypoint.sh`.

Put Nginx or Caddy in front of it for TLS/HTTPS termination. A minimal Caddy
example (`Caddyfile`):
```
yourdomain.com {
    reverse_proxy localhost:8000
}
```
Caddy handles Let's Encrypt certificates automatically.

### 5.2 Deploy to Render.com (managed, least ops work)

1. Push this repo to GitHub.
2. In Render: **New → Blueprint**, point it at your repo — it reads
   `render.yaml` and provisions everything automatically: web service,
   Celery worker, Celery beat, a free PostgreSQL database, and a free Redis
   instance, all wired together.
3. After the first deploy, open the **Shell** tab on the web service and run:
   ```bash
   python manage.py createsuperuser
   python manage.py shell < seed_categories.py
   ```
4. For real email delivery, add `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` /
   etc. as environment variables on the web, worker, and beat services (set
   `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`).

### 5.3 Deploy to Railway

Same idea as Render: create a project from the GitHub repo, Railway detects
the `Dockerfile` automatically. Add a PostgreSQL and Redis plugin from
Railway's marketplace, then add three services from the same repo/image:
one running the default `CMD` (web), one with start command
`celery -A budgetproject worker -l info`, and one with
`celery -A budgetproject beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`.
Set `RUN_MIGRATIONS=false` on the worker and beat services so only the web
service runs migrations on boot.

### 5.4 Pre-launch checklist

- [ ] `SECRET_KEY` is a real random value, not the dev default
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` set to your actual domain(s)
- [ ] `CSRF_TRUSTED_ORIGINS` includes `https://yourdomain.com`
- [ ] Using PostgreSQL, not SQLite (`DATABASE_URL` set)
- [ ] `EMAIL_BACKEND` switched from console to SMTP, with real credentials
- [ ] HTTPS is enforced (`SECURE_SSL_REDIRECT`, on by default when `DEBUG=False`)
- [ ] Celery `worker` and `beat` are both running as persistent services —
      if `beat` isn't running, weekly/monthly emails simply never fire
- [ ] `python manage.py collectstatic` has run (the Dockerfile does this
      automatically at build time)
- [ ] Test the weekly/monthly email pipeline once manually before relying on
      the schedule:
      ```bash
      python manage.py shell -c "
      from core.tasks import send_weekly_report_for_user
      from accounts.models import User
      send_weekly_report_for_user(User.objects.first().id)
      "
      ```

## 6. Notes on design decisions

- **Email-only login**: custom `User` model (`accounts.User`) with
  `USERNAME_FIELD = "email"`, no username field.
- **Category scoping**: categories with `user=None` are global/shared
  defaults; categories with a `user` FK are private to that user.
- **transaction_type de-dupe**: `Transaction.transaction_type` is validated
  in `TransactionForm.clean()` to match its `category.type`, so the two
  can't drift out of sync.
- **All PDF and email reports share one calculation path** (`core/utils.py:
  compute_period_stats`) so the dashboard, downloadable PDFs, and emailed
  PDFs always agree on the numbers.
