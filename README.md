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
- **Framework:** React 18
- **Styling:** Tailwind CSS
- **UI Components:** Material UI
- **HTTP Client:** Axios
- **Build Tool:** Vite

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
│   │   └── utils/              # Helpers (JWT, hashing, config)
│   ├── migrations/             # Alembic migrations
│   │   └── versions/
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

6. Run migrations:
```bash
alembic upgrade head
```

7. Run server:
```bash
uvicorn app.main:app --reload
```

Server will be available at: http://localhost:8000

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
cp .env.example .env.local
```

4. Start development server:
```bash
npm run dev
```

App will be available at: http://localhost:5173

## 📖 API Documentation

Once backend is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 📚 Documentation

All project documentation lives in [`docs/`](./docs):

- **Backend:** `backend/requirements.txt`, `backend/.env.example`
- **Frontend:** `frontend/package.json`, `frontend/.env.example`
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
