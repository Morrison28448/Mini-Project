## Intern Logbook System (Django)

### Overview
This is a Django-based Intern Logbook system for recording intern tasks and enabling HR/Supervisors to monitor and export reports. The app includes role-based dashboards, CSV export, and admin-managed intern accounts.

### Roles
- **Interns**
  - Log in and submit daily task entries.
  - View task history and toggle status ("Pending"/"Resolved").
- **HR/Supervisors (Admins/Staff)**
  - Log in to view/filter all intern tasks by date range, status, staff ID, and intern name.
  - Download filtered results as CSV.
  - Manage intern accounts via the Django admin.

## Tech Stack
- **Backend**: Django
- **Database**: SQLite (default, file `db.sqlite3`)
- **Frontend**: HTML, CSS, Bootstrap 5
- **Auth**: Django authentication (email as username), role-based routing

## Project Structure (key files)
- `manage.py`: Django management entry point
- `internlog/`:
  - `settings.py`: project settings, apps, templates, database, auth redirects
  - `urls.py`: root routing
- `logs/`:
  - `models.py`: `Intern`, `Staff`, `Task`, plus enums
  - `views.py`: intern and HR views, CSV export, role redirect
  - `urls.py`: app-level routes
  - `admin.py`: admin registration for models
  - `forms.py`: forms for tasks and HR filtering
  - `migrations/`: Django migrations for tables
- `templates/`:
  - `base.html`: base layout and navbar
  - `auth/login.html`: login page
  - `intern/dashboard.html`: intern dashboard (form + history)
  - `intern/task_form.html`: new task page
  - `hr/dashboard.html`: HR dashboard (filters + table + CSV)

## Data Model
- `Intern`
  - `name`, `email`, `password` (stored in intern table for metadata), `department`
  - `user`: OneToOne to Django `User` for authentication
- `Staff`
  - `name`, `department`, `position`
- `Task`
  - `intern` (FK to Intern), `staff` (optional FK to Staff)
  - `task_description`, `date`, `status` (Pending/Resolved), `remarks`
  - `created_at`, `updated_at` timestamps

## Routing and URLs
- **Authentication**
  - `/login/`: Login page
  - `/logout/`: Logout
- **Role Redirect**
  - `/`: `dashboard_redirect` decides landing page:
    - Staff → `/hr/`
    - Intern → `/intern/`
    - Others → back to `/login/` with an error
- **Intern Dashboard**
  - `/intern/`: Dashboard with logbook form and task history
  - `/task/create/`: Create a task
  - `/task/<id>/update-status/`: Toggle task status
- **HR/Supervisor Dashboard**
  - `/hr/`: Filters + table of all tasks
  - `/hr/export/csv/`: Download CSV (respects current filters)
- **Admin**
  - `/admin/`: Django admin for managing `User`, `Intern`, `Staff`, `Task`

## Authentication and Roles
- Intern accounts are created by Admins in `/admin/`.
- Admins/staff are Django `User` objects with `is_staff=True`.
- Post-login redirect uses `LOGIN_REDIRECT_URL = 'dashboard_redirect'` to route users to the appropriate dashboard.

## Setup and Running
1) Create and activate venv (PowerShell)
```powershell
python -m venv .venv
\.\.venv\Scripts\Activate.ps1
```

2) Install dependencies
```powershell
pip install -r requirements.txt
```

3) Apply migrations
```powershell
python manage.py makemigrations
python manage.py migrate
```

4) Create an admin user (HR/Supervisor)
```powershell
python manage.py createsuperuser
```

5) Run the server
```powershell
python manage.py runserver
```

## Admin Management Flow
1. Visit `/admin/` and log in as superuser.
2. Create a `User` for each intern (do NOT check `is_staff`).
3. Create a linked `Intern` profile in `logs.Intern`, selecting the newly created `User`.
4. Optionally, seed `Staff` entries for assigning/attributing tasks.

Interns will then:
- Log in at `/login/` → redirected to `/intern/`.
- Submit daily tasks and view history.

Admins will:
- Log in at `/login/` → redirected to `/hr/`.
- Filter results and export CSV.

## UI Features
- Bootstrap 5 styling
- Base layout (`templates/base.html`) with auth-aware navbar
- Intern Dashboard: form (date, description, staff, status) + history with toggle
- HR Dashboard: filters (start date, end date, status, staff ID, intern name), table, CSV export

## CSV Export
- Endpoint: `/hr/export/csv/`
- Returns a streaming CSV file with fields:
  - Intern name, email, department, staff name, date, status, task description, remarks
- Honors same filters as the HR dashboard (via query parameters).

## Configuration Highlights
- `internlog/settings.py`:
  - `INSTALLED_APPS` includes `logs`
  - Templates directory includes `templates/`
  - SQLite default DB
  - Auth redirects:
    - `LOGIN_URL = 'login'`
    - `LOGIN_REDIRECT_URL = 'dashboard_redirect'`
    - `LOGOUT_REDIRECT_URL = 'login'`

## Deployment Notes
- Replace `SECRET_KEY` with a secure value via environment variable `DJANGO_SECRET_KEY`.
- Set `DEBUG=False` and restrict `ALLOWED_HOSTS` for production.
- Use PostgreSQL or another production-grade database instead of SQLite.
- Serve static files via a proper static server or storage (e.g., WhiteNoise, CDN).

## Security Considerations
- Interns cannot self-register; accounts are managed by Admins.
- Access controls:
  - Intern views require an `Intern` profile to proceed.
  - HR views require `is_staff=True`.
- CSRF protection is enabled via Django middleware and template tags.

## Troubleshooting
- Error: “no such table: logs_intern”
  - Ensure migrations exist: `logs/migrations/__init__.py`
  - Run:
    ```powershell
    python manage.py makemigrations logs
    python manage.py migrate
    ```
  - Restart the dev server.
- Login loops back to login page
  - Ensure cookies are enabled.
  - Verify user credentials.
  - For intern accounts, ensure `User` is linked to an `Intern` via `intern_profile`.
- Access denied to `/hr/`
  - Ensure the user has `is_staff=True` (set in `/admin/`).

## Future Enhancements (optional)
- HR inline editing of task remarks/status on `/hr/` without navigating away.
- Staff directory picker instead of free ID entry.
- File attachments for tasks.
- Department-based access controls for supervisors.
- Pagination on HR dashboard for large datasets.


