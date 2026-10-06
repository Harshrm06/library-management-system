# Library Management System - Setup Guide

Complete setup instructions for the Library Management System.

## Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.14.7+ | Backend runtime |
| Node.js | 18+ | Frontend build tool (Vite) |
| Git | 2.0+ | Version control |

### Windows
- Install Python from [python.org](https://python.org) (check "Add to PATH")
- Install Node.js from [nodejs.org](https://nodejs.org)

### Linux/macOS
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-venv nodejs npm

# macOS (Homebrew)
brew install python node
```

## One-Click Startup

From the project root directory:

### Windows PowerShell
```powershell
.\start_project.ps1
```

### Linux/macOS
```bash
chmod +x start_project.sh
./start_project.sh
```

This starts both servers:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| **Administrator** | `admin@library.local` | `Admin123` |
| **Member** | `member@library.local` | `Member123` |

> ⚠️ **Important:** These are development credentials. Change both passwords and the `JWT_SECRET` in `backend/.env` before any production deployment.

## What the Startup Scripts Do

### Master Script (`start_project.ps1` / `start_project.sh`)
1. Validates project structure
2. Launches backend in new window/background
3. Waits 5 seconds for database initialization
4. Launches frontend in new window/background
5. Displays URLs and credentials

### Backend Script (`backend/run.ps1` / `backend/run.sh`)
1. Creates `.env` from `.env.example` if missing
2. Activates Python virtual environment (`venv/`)
3. Runs database migrations (Alembic)
4. Seeds database with 8 books + 2 users
5. Starts uvicorn server on `0.0.0.0:8000` with auto-reload

### Frontend Script (`frontend/run.ps1` / `frontend/run.sh`)
1. Installs npm dependencies if `node_modules/` missing
2. Starts Vite dev server on `localhost:5173`

## Manual Setup (Alternative)

If you prefer step-by-step:

### Backend
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env - at minimum generate a new JWT_SECRET:
# python -c "import secrets; print(secrets.token_urlsafe(48))"

# Initialize database
python seed_data.py

# Start server
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

## Verification Checklist

After startup, verify:

- [ ] Frontend loads at http://localhost:5173
- [ ] Backend health check: `curl http://localhost:8000/health` returns `{"status":"ok"}`
- [ ] API docs accessible at http://localhost:8000/docs
- [ ] Can login as admin: `admin@library.local` / `Admin123`
- [ ] Can login as member: `member@library.local` / `Member123`
- [ ] Book catalog shows 8 books
- [ ] Can borrow a book as member
- [ ] Can view borrowing history

## Troubleshooting

### "Virtual environment not found"
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### "node_modules not found" / npm errors
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### "Address already in use" (port 8000 or 5173)
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8000
kill -9 <PID>
```

### Database migration errors
```bash
cd backend
source venv/bin/activate
rm library_db.db
python seed_data.py --reset
```

### CORS errors (frontend can't call backend)
Check `backend/.env`:
```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Frontend shows "Network Error"
1. Verify backend is running on port 8000
2. Check `frontend/.env` has `VITE_API_URL=http://localhost:8000/api`
3. Restart both servers

### Seed data not loading
```bash
cd backend
source venv/bin/activate
python seed_data.py --reset
```

## Production Deployment Checklist

- [ ] Generate secure `JWT_SECRET`: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- [ ] Set `DEBUG=False` in `backend/.env`
- [ ] Change default passwords for admin and member accounts
- [ ] Use MySQL/PostgreSQL instead of SQLite
- [ ] Set up reverse proxy (nginx) with SSL
- [ ] Run `npm run build` in frontend for production assets
- [ ] Use gunicorn: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
- [ ] Configure proper logging and monitoring

## File Structure

```
library-management-system/
├── start_project.ps1      # Windows master startup
├── start_project.sh       # Linux/macOS master startup
├── SETUP.md               # This file
├── README.md              # Project overview
├── .gitignore
├── backend/
│   ├── run.ps1            # Windows backend startup
│   ├── run.sh             # Linux/macOS backend startup
│   ├── seed_data.py       # Database seeder
│   ├── requirements.txt   # Python dependencies
│   ├── .env.example       # Environment template
│   ├── alembic/           # Migrations
│   └── app/               # FastAPI application
└── frontend/
    ├── run.ps1            # Windows frontend startup
    ├── run.sh             # Linux/macOS frontend startup
    ├── package.json       # npm dependencies
    ├── vite.config.js     # Vite configuration
    └── src/               # React source code
```

## Support

For issues:
1. Check the troubleshooting section above
2. Verify all prerequisites are installed
3. Ensure ports 5173 and 8000 are available
4. Check console output for error messages