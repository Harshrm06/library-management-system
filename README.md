# Library Management System

A full-stack web application for library book management with user authentication, book catalog, and borrowing system.

## 📋 Features

- **User Authentication:** Registration, login with JWT tokens
- **Book Management:** Search, filter, and browse library catalog
- **Borrowing System:** Borrow books, track borrowing history, return books
- **Admin Dashboard:** Manage books, view statistics, manage users
- **Role-Based Access:** Admin and Member roles with different permissions

## 🛠 Tech Stack

### Backend
- **Framework:** FastAPI
- **Database:** MySQL with SQLAlchemy ORM
- **Authentication:** JWT (JSON Web Tokens)
- **Password Hashing:** bcrypt
- **Migrations:** Alembic

### Frontend
- **Framework:** React 18 with React Router 6
- **Styling:** Tailwind CSS 3
- **UI Components:** Material UI 5 (form controls, chips, alerts)
- **HTTP Client:** Axios 1 (interceptors attach the bearer token)
- **Build Tool:** Vite 5

## 📂 Project Structure

```
library-management-system/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── controllers/        # Request handling / business logic
│   │   ├── middleware/         # Custom middleware (auth, logging)
│   │   ├── models/             # SQLAlchemy models
│   │   ├── routes/             # API route definitions
│   │   ├── schemas/            # Pydantic schemas
│   │   └── utils/              # Helpers (JWT, hashing, validators)
│   ├── alembic.ini              # Alembic configuration
│   ├── alembic/                 # Migration environment
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/            # Revision scripts
│   ├── logs/                   # Application logs (git-ignored)
│   ├── .env.example            # Environment template
│   └── requirements.txt
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── pages/              # Route-level screens
│   │   ├── components/         # Reusable UI components
│   │   ├── context/            # React context providers
│   │   ├── services/           # API client modules
│   │   ├── hooks/              # Custom hooks
│   │   ├── utils/              # Helper functions
│   │   ├── styles/             # CSS / Tailwind entry files
│   │   └── App.jsx
│   ├── .env.example            # Environment template
│   └── package.json
├── docs/                       # Project documentation
├── .gitignore
└── README.md
```

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+
- MySQL 8.0+

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. Create MySQL database:
```bash
mysql -u root -p
CREATE DATABASE library_db;
EXIT;
```

6. Run migrations (see [Database Migrations](#database-migrations)):
```bash
alembic upgrade head
```

7. Run server:
```bash
uvicorn app.main:app --reload
```

Server will be available at: http://localhost:8000 (`GET /health` for a liveness check, `/docs` for Swagger)

### Database Migrations

Schema changes are versioned with [Alembic](https://alembic.sqlalchemy.org/).
Configuration lives in `backend/alembic.ini` and `backend/alembic/env.py`; the
database URL is read from `DATABASE_URL` in `backend/.env`, never from the ini
file. Run every command from `backend/`.

**Apply migrations**

```bash
alembic upgrade head        # apply everything
alembic upgrade +1          # apply one step
alembic current             # show the applied revision
```

**Create a new migration**

```bash
# 1. change the model in app/models/
alembic revision --autogenerate -m "Initial migration: Create users and books tables"
# 2. read the generated file in alembic/versions/, fix anything Alembic guessed
# 3. prove both directions work
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

**Roll back**

```bash
alembic downgrade -1        # undo the last revision
alembic downgrade <id>      # undo down to a specific revision
alembic downgrade base      # undo everything
```

The first revision, `alembic/versions/001_initial_migration.py`, creates the
`users` and `books` tables with their unique constraints and indexes. See
[`docs/MIGRATION_GUIDE.md`](./docs/MIGRATION_GUIDE.md) for merge/conflict
handling and best practices.

### Available Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/health` | No | Service health check |
| `GET` | `/` | No | Service metadata |
| `POST` | `/api/auth/register` | No | Create a member account (201) |
| `POST` | `/api/auth/login` | No | Exchange credentials for a JWT |
| `GET` | `/api/auth/me` | Bearer | Return the authenticated profile |
| `PUT` | `/api/auth/me` | Bearer | Update the authenticated profile |
| `POST` | `/api/auth/refresh-token` | Bearer | Issue a new token for the caller |
| `POST` | `/api/auth/logout` | Bearer | Acknowledge logout (stateless) |

### Response Format

Successful responses use a `{ success, message, data, timestamp }` envelope and
errors use `{ success: false, message, error, code, timestamp }`.

```jsonc
// POST /api/auth/login
{
  "success": true,
  "message": "Login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": { "id": 1, "email": "member@example.com", "role": "member", "...": "..." }
  },
  "timestamp": "2026-01-01T12:00:00+00:00"
}
```

Registration accepts passwords of at least 6 characters containing at least one
letter and one number. Passwords are hashed with bcrypt and never returned.

### Database Tables

Tables are declared in `backend/app/models/` (`users`, `books`) and created by
Alembic revision `001_initial_migration.py`:

```bash
alembic upgrade head
```

For throwaway experiments only, the metadata can be pushed directly:

```python
from app.database import Base, engine
Base.metadata.create_all(bind=engine)
```

Do not mix the two: `create_all()` leaves Alembic unaware of the schema, and
the next `upgrade head` will fail with "table already exists".

### Verifying the Backend

A standalone script checks every backend component without needing MySQL:

```bash
python backend/test_verification.py
```

It prints one line per assertion (`✅` / `❌`), a `X/Y tests passed` summary
and exits non-zero on failure. Useful environment switches:

| Variable | Effect |
| --- | --- |
| `VERIFY_ASCII=1` | Use `[PASS]` / `[FAIL]` instead of the Unicode markers |
| `VERIFY_LOGS=1` | Keep the application's INFO/WARNING log output |

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env.local` from `.env.example`:
```bash
cp .env.example .env.local     # Windows: copy .env.example .env.local
# VITE_API_BASE_URL=http://localhost:8000
```

4. Start development server:
```bash
npm run dev
```

App will be available at: http://localhost:5173

### Frontend Structure

```
frontend/
├── index.html
├── vite.config.js               # Vite + React plugin, /api dev proxy
├── tailwind.config.js           # Tailwind theme (brand + ink palettes)
├── postcss.config.js            # Tailwind + autoprefixer
├── .eslintrc.cjs                # ESLint 8 config used by `npm run lint`
└── src/
    ├── main.jsx                 # Mounts React, BrowserRouter, AuthProvider
    ├── App.jsx                  # Routes and public/protected split
    ├── pages/                   # Login, Register, Catalog, Detail, 404, 403
    ├── components/              # Header, ProtectedRoute, ErrorBoundary, BookCard,
    │                            # FormInput, FormError, LoadingSpinner, Toast, Skeleton
    ├── context/AuthContext.jsx  # Session state (token + user) and actions
    ├── hooks/useAuth.js         # Access the auth context
    ├── services/                # api.js (axios), authService.js (endpoints)
    ├── utils/                   # validators.js, constants.js, helpers.js
    └── styles/index.css         # Tailwind directives + component classes
```

| Script | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server on :5173, proxying `/api` to :8000 |
| `npm run build` | Production bundle into `dist/` |
| `npm run preview` | Serve the production bundle locally |
| `npm run lint` | ESLint over `src` |

## 📖 API Documentation

Once backend is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 📚 Documentation

All project documentation lives in [`docs/`](./docs):

- **Backend:** `backend/requirements.txt`, `backend/.env.example`
- **Frontend:** `frontend/package.json`, `frontend/.env.example`
- **Database migrations:** [`docs/MIGRATION_GUIDE.md`](./docs/MIGRATION_GUIDE.md)
- **Product requirements:** `Library_Management_System_PRD.md` (repository root)
- **Planned docs:** `docs/API.md`, `docs/DATABASE.md` (added during backend scaffolding)

## 👥 Team

- **Team Member 1 (Path A):** Backend Auth + Book Management, Frontend Auth + Book Catalog
- **Team Member 2 (Path B):** Backend Borrowing + Admin, Frontend Borrowing History + Admin Dashboard

## 📋 Development Workflow

1. Create feature branch from `dev`
2. Commit with clear messages
3. Push to GitHub
4. Create Pull Request
5. Code review
6. Merge to `dev`
7. Final merge to `main` after integration

## 🔒 Security

- Passwords hashed with bcrypt
- JWT tokens for authentication
- Role-based access control
- CORS configured for frontend
- Environment variables for sensitive data

## 📝 License

MIT License - Feel free to use this project for educational purposes.

## 🤝 Contributing

Pull requests welcome! Please follow the project structure and coding standards.

---
