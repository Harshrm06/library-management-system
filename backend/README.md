# Library Management System - Backend API

A FastAPI-based REST API for managing a library system with books, users, and borrowing records.

## Quick Start

**One command to run everything:**

```powershell
# Windows PowerShell (from project root)
.\start_project.ps1
```

```bash
# Linux/macOS (from project root)
./start_project.sh
```

Or run backend only:

```powershell
# Windows PowerShell
cd backend
.\run.ps1
```

```bash
# Linux/macOS
cd backend
./run.sh
```

The script will:
1. Create `.env` from `.env.example` if missing
2. Activate virtual environment
3. Run database migrations and seed data
4. Start uvicorn server on `http://0.0.0.0:8000`

## Project Structure

```
backend/
├── app/
│   ├── config.py          # Application settings (pydantic)
│   ├── database.py        # SQLAlchemy engine & session
│   ├── main.py            # FastAPI app entry point
│   ├── middleware/        # Auth middleware
│   ├── models/            # SQLAlchemy models
│   │   ├── user.py
│   │   ├── book.py
│   │   └── borrowing_record.py
│   ├── routes/            # API route handlers
│   │   ├── auth_routes.py
│   │   ├── book_routes.py
│   │   └── borrowing_routes.py
│   ├── schemas/           # Pydantic request/response models
│   └── utils/             # Helper utilities
├── alembic/               # Database migrations
├── seed_data.py           # Database seeding script
├── requirements.txt       # Python dependencies
├── run.ps1                # Windows startup script
├── run.sh                 # Linux/macOS startup script
└── .env.example           # Environment template
```

## API Endpoints

### Authentication (4 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT token |
| GET | `/api/auth/me` | Get current user profile |
| PUT | `/api/auth/me` | Update current user profile |

### Books (6 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/books` | List all books (paginated, filterable) |
| GET | `/api/books/{id}` | Get book by ID |
| POST | `/api/books` | Create new book (admin only) |
| PUT | `/api/books/{id}` | Update book (admin only) |
| DELETE | `/api/books/{id}` | Delete book (admin only) |
| GET | `/api/books/search?q={query}` | Search books by title/author/ISBN |

### Borrowing (10 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/borrow` | Borrow a book |
| POST | `/api/return/{record_id}` | Return a borrowed book |
| GET | `/api/borrow/history` | Get current user's borrowing history |
| GET | `/api/borrow/active` | Get current user's active borrows |
| GET | `/api/borrow/overdue` | Get overdue books (admin) |
| GET | `/api/borrow/all` | Get all borrowing records (admin) |
| GET | `/api/borrow/{record_id}` | Get borrowing record by ID |
| PUT | `/api/borrow/{record_id}/extend` | Extend due date (admin) |
| GET | `/api/borrow/stats` | Get borrowing statistics (admin) |
| GET | `/api/borrow/book/{book_id}/history` | Get borrowing history for a book |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check endpoint |

## Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@library.local&password=Admin123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in the Authorization header:

```bash
curl -H "Authorization: Bearer <your_token>" http://localhost:8000/api/auth/me
```

## Default Credentials

After running `seed_data.py` (or `run.ps1`/`run.sh` which run it automatically):

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@library.local | Admin123 |
| Member | member@library.local | Member123 |

**⚠️ Change these passwords and the JWT_SECRET in `.env` before production use!**

## Database

- **Type:** SQLite (default) or MySQL
- **Location:** `backend/library_db.db` (SQLite file)
- **Migrations:** Managed by Alembic in `alembic/versions/`
- **Seed Data:** 8 classic books + 2 users (admin + member)

### Switching to MySQL

Update `.env`:
```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/library_db
```

## Development

### Running Tests

```bash
cd backend
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1
pytest
```

### Adding Migrations

```bash
# After modifying models
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Database Reset

```bash
cd backend
source venv/bin/activate
python seed_data.py --reset
```

## Troubleshooting

### "Module not found" errors
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### "Address already in use" on port 8000
```bash
# Find and kill process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS:
lsof -i :8000
kill -9 <PID>
```

### Database locked / migration errors
```bash
cd backend
rm library_db.db
python seed_data.py --reset
```

### CORS errors in frontend
Ensure `.env` has correct `CORS_ORIGINS`:
```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Frontend can't connect to backend
1. Check backend is running on port 8000
2. Check `VITE_API_URL` in frontend `.env` (defaults to `http://localhost:8000/api`)
3. Check CORS settings in backend `.env`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./library_db.db` | Database connection string |
| `JWT_SECRET` | *(required)* | Secret key for JWT signing |
| `JWT_EXPIRY_HOURS` | `24` | Token lifetime |
| `DEBUG` | `False` | Debug mode |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |

## Production Deployment

1. Generate secure JWT secret:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. Update `.env`:
   ```env
   JWT_SECRET=<generated-secret>
   DEBUG=False
   ```

3. Use a production ASGI server:
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
   ```

4. Use reverse proxy (nginx) for SSL termination