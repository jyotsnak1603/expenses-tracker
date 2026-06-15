# FairShare — Shared Expenses Tracker

A shared expenses app built for a group of flatmates who were tracking expenses in a spreadsheet. It got messy fast — wrong formats, duplicate entries, a settlement logged as an expense, currency confusion. This app cleans all that up and gives everyone a clear picture of who owes whom.

**Live App:** https://expenses-tracker-qn4qla1l6-jyotsnak1603s-projects.vercel.app/

**GitHub:** https://github.com/jyotsnak1603/expenses-tracker

---

## What it does

- Login and register (JWT auth)
- Create groups with time-based membership (members can join and leave, balances adjust accordingly)
- Add expenses with equal, unequal, percentage, and share-based splits
- Multi-currency support — trip expenses in USD get converted to INR at a fixed rate
- Import the original CSV with a step-by-step anomaly review — every data problem is shown to the user before anything is saved
- Settlement recording and optimized "who pays whom" summary

---

## Tech Stack

**Backend:** Django 5.2, Django REST Framework, SimpleJWT, PostgreSQL, Gunicorn, WhiteNoise

**Frontend:** React (Vite), Tailwind CSS, Axios, Framer Motion

**Deployment:** Backend on Render, Frontend on Vercel, DB on Render PostgreSQL

**AI Used:** Antigravity AI (Google DeepMind) — see `AI_USAGE.md` for details

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (or SQLite for local dev)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Create a .env file (or set these in your environment)
# SECRET_KEY=your-secret-key-here
# DATABASE_URL=sqlite:///db.sqlite3   (for local dev)
# DEBUG=True

python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend proxies `/api` to `localhost:8000` by default (configured in `vite.config.js`).

For production, set the `VITE_API_BASE_URL` environment variable to your backend URL.

---

## Environment Variables

### Backend (Render)
| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `FRONTEND_URL` | Vercel URL (for CORS) |
| `DEBUG` | Set to `False` in production |

### Frontend (Vercel)
| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Full URL of the Django backend |

---

## Importing the CSV

1. Log in and create a group.
2. Click "Import CSV" in the navbar.
3. Upload `expenses_export.csv`.
4. The app shows every anomaly it found with the severity level and a suggested fix.
5. Review and confirm.
6. Done — all valid expenses are saved to the database.

---

## Project Structure

```
expenses/
├── backend/
│   ├── accounts/       # Auth (register, login, JWT)
│   ├── groups/         # Groups and memberships
│   ├── expenses/       # Expenses, splits, settlements, balance engine
│   ├── importer/       # CSV parser, anomaly detector, import views
│   └── config/         # Django settings, URLs
├── frontend/
│   └── src/
│       ├── pages/      # Home, Dashboard, GroupDetail, ImportCSV, Login, Register
│       ├── api/        # Axios setup with JWT interceptors
│       └── context/    # Auth context
├── README.md
├── SCOPE.md
├── DECISIONS.md
├── AI_USAGE.md
└── IMPORT_REPORT.md
```
