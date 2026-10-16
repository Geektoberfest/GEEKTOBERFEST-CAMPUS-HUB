# CampusHub

CampusHub is a small Flask-based student productivity and campus-management app for college open-source events. It keeps tasks, deadlines, notes, shared resources, announcements, notifications and basic productivity stats in one place.

## Features
- Student registration/login/logout with hashed passwords and sessions
- Student-only private tasks and notes
- Task CRUD, priorities, categories, due dates, search and filters
- Deadline view with automatic overdue/today/upcoming states
- Notes CRUD and search
- Shared resources with admin-only management
- Campus announcements with admin-only publishing/deletion
- In-app reminders for overdue and tomorrow-due tasks
- Dashboard statistics calculated from SQLite data
- Student profile editing
- Admin dashboard and system counts
- JSON API for core modules
- Backend validation, CSRF protection and authorization checks
- Responsive desktop/tablet/mobile UI
- Pytest suite and GitHub Actions CI

## Tech stack
Python, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, SQLite, Jinja, HTML, CSS and vanilla JavaScript.

## Project structure
```text
campushub/
├── app/
│   ├── models/
│   ├── routes/              # auth, student pages/API, admin
│   ├── services/            # dashboard/reminder logic
│   ├── templates/
│   ├── static/css/          # shared styling
│   ├── static/js/           # page-specific browser logic
│   ├── utils/
│   ├── extensions.py
│   ├── seed.py
│   └── __init__.py
├── tests/
├── .github/workflows/tests.yml
├── .env.example
├── config.py
├── requirements.txt
├── run.py
├── CONTRIBUTING.md
└── README.md
```

## Windows setup
```powershell
git clone <repository-url>
cd campushub
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```
Open `http://127.0.0.1:5000`.

## Linux/macOS setup
```bash
git clone <repository-url>
cd campushub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```
Open `http://127.0.0.1:5000`.

## Demo data
The repository includes a seed function. To seed a fresh database, run:
```bash
python -c "from app import create_app; from app.seed import seed_database; app=create_app(); app.app_context().push(); seed_database()"
```
Demo credentials:
- Student: `student@campushub.local` / `Student@12345`
- Admin: `admin@campushub.local` / `Admin@12345`

Change these credentials before using a deployed environment. They are demo-only accounts.

## Environment
Copy `.env.example` to `.env`:
- `SECRET_KEY`: random application secret
- `DATABASE_URL`: SQLAlchemy database URL; SQLite is the default
- `SESSION_COOKIE_SECURE`: set `true` behind HTTPS
- `FLASK_ENV`: local development setting

## API overview
All JSON endpoints return `{success, data}` on success and `{success:false,error}` on failure.

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | No | Register |
| POST | `/api/auth/login` | No | Session login |
| POST | `/api/auth/logout` | Yes | Session logout |
| GET/POST | `/api/tasks` | Student | List/create tasks |
| PUT/DELETE | `/api/tasks/<id>` | Owner | Update/delete task |
| GET/POST | `/api/notes` | Student | List/create notes |
| PUT/DELETE | `/api/notes/<id>` | Owner | Update/delete note |
| GET | `/api/resources` | Yes | Search/filter resources |
| GET | `/api/announcements` | Yes | Search/filter announcements |
| GET | `/api/dashboard` | Student | Dashboard stats |
| GET | `/api/notifications` | Student | Notifications |

## Database backup and restore
CampusHub includes CLI commands to backup and restore application data with safeguards against accidental data loss.

### Creating a backup
```bash
# JSON format backup (default) saved to instance/backups/
flask db-backup

# Custom destination path
flask db-backup -o custom_backup.json

# SQLite format backup
flask db-backup -f sqlite -o custom_backup.db
```

### Restoring a backup
```bash
# Interactive restore (prompts for confirmation and creates a pre-restore safety backup)
flask db-restore -i instance/backups/campushub_backup_example.json

# Non-interactive restore with confirmation flag
flask db-restore -i custom_backup.json --yes

# Restore without automatic safety backup
flask db-restore -i custom_backup.json --yes --no-safety-backup
```

## Testing

```bash
pytest -q
```
The GitHub Actions workflow runs the same suite on pushes and pull requests.

## Screenshots
Add event screenshots here after the team captures the local demo UI.

## Contribution levels
Beginner issues focus on docs, accessibility, small UI improvements and tests. Intermediate issues add isolated API/UI features. Advanced issues cover deeper architecture, query optimization, security hardening and analytics.

## Merge-conflict guidance
Avoid broad edits to `style.css`, `models.py`, or large templates. Prefer page-specific JS, route modules and small services. If an issue touches a shared file, keep the PR narrowly scoped and rebase before requesting review.
