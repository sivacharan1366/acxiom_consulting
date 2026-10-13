# Acxiom CRM

A lightweight Customer Relationship Management (CRM) web application built with **Python, Flask, and SQLite**. It is intended as a simple, locally runnable CRM demo for managing customers, leads, opportunities, follow-ups, and activities.

## Features

- **Authentication** with password hashing and temporary lockout after repeated failed login attempts
- **Role-based access** for Admin, Manager, and Sales users
- **Dashboard** with CRM record counts and weighted opportunity pipeline
- **Customer management**
- **Lead management** and qualified-lead conversion
- **Opportunity management**
- **Follow-up tracking**
- **Activity tracking**
- **Reports**
- **Audit log** access restricted to privileged roles
- **JSON API** for supported CRM data
- **Basic client-side form validation**

> This is a learning/demo project. Review the code and complete security, authorization, validation, and deployment hardening before using it with real customer data or exposing it publicly.

## Technology stack

- Python
- Flask
- SQLite
- Werkzeug password hashing

## Requirements

- Python 3.10+ recommended
- `pip`

## Run locally

### 1. Clone the repository

```bash
git clone https://github.com/sivacharan1366/acxiom_consulting.git
cd acxiom_consulting
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the Python executable directly with `.venv\Scripts\python.exe`.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Start the application

```powershell
python app.py
```

Open the local address printed in the terminal (typically `http://127.0.0.1:5000`).

The SQLite database is created locally when the app initializes. Keep database files out of Git and never commit real customer data.

## Demo accounts

The current development seed accounts are:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@12345` |
| Manager | `manager` | `Manager@12345` |
| Sales | `sales` | `Sales@12345` |

These are **development-only demo credentials**. Change or remove them before any public deployment. Do not use these credentials for a production system.

## Project files

```text
acxiom_consulting/
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

The `.venv/` directory and local SQLite database files should remain untracked.

## API

The application exposes a JSON endpoint in the form:

```text
/api/<table>
```

For example, while signed in locally, visit:

```text
http://127.0.0.1:5000/api/customers
```

Only use endpoints with authorized demo data. Review API authorization and data scoping before deploying or exposing the application.

## Known limitations

- This is a compact prototype, not a production-hardened CRM.
- Some CRUD flows and role/ownership checks may be incomplete; verify them against the assignment requirements.
- Client-side validation improves usability but must be backed by server-side validation.
- Configure a strong secret key using an environment variable before deployment.
- Use HTTPS, secure cookie settings, appropriate CSRF protection, and production-grade deployment configuration before making the app public.
- Do not store real customer information in a public demo.

## Development

Make changes in `app.py`, test each affected role and workflow locally, then commit the intended files only:

```powershell
git status
git add README.md app.py requirements.txt .gitignore
git commit -m "Update CRM documentation"
git push origin main
```

## License

No license has been specified yet. Contact the repository owner before reusing this project.
