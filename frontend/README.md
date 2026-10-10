# Library Management System - Frontend

A React 18 + TypeScript-free single-page application for the Library Management System. Built with Vite, Tailwind CSS, and MUI components.

## Tech Stack

- **Build tool:** Vite
- **Frontend library:** React 18 (JSX)
- **Styling:** Tailwind CSS + MUI (Material-UI)
- **HTTP client:** Axios
- **Routing:** React Router DOM
- **State management:** React Context (AuthContext)

## Project Structure

```
frontend/
├── public/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── Header.jsx             # App header with navigation
│   │   ├── ProtectedRoute.jsx     # Route guard (auth + role)
│   │   ├── LoadingSpinner.jsx     # Full-screen and inline loaders
│   │   ├── Toast.jsx              # Transient notification banner
│   │   ├── Skeleton.jsx           # Content placeholder
│   │   ├── BookCard.jsx           # Book card component
│   │   ├── BorrowModal.jsx        # Borrow confirmation modal
│   │   ├── ApiEventBridge.jsx     # API event listener (toasts)
│   │   ├── ErrorBoundary.jsx      # Global error boundary
│   │   ├── FormInput.jsx          # Reusable form input
│   │   └── FormError.jsx          # Field error display
│   ├── hooks/
│   │   ├── useAuth.js             # Auth context hook
│   │   └── useDebounce.js         # Debounced value hook
│   ├── context/
│   │   └── AuthContext.jsx        # Auth state provider
│   ├── pages/                     # Route pages
│   │   ├── LoginPage.jsx
│   │   ├── RegisterPage.jsx
│   │   ├── DashboardPage.jsx
│   │   ├── BookCatalogPage.jsx    # Browse/search books
│   │   ├── BookDetailPage.jsx     # Book detail + borrow
│   │   ├── BorrowingHistoryPage.jsx
│   │   ├── ProfilePage.jsx
│   │   ├── AdminDashboardPage.jsx
│   │   ├── AdminUsersPage.jsx
│   │   ├── AdminBooksPage.jsx
│   │   ├── AdminBorrowingHistoryPage.jsx
│   │   ├── UnauthorizedPage.jsx
│   │   └── NotFoundPage.jsx
│   ├── services/                  # API service modules
│   │   ├── api.js                 # Base axios instance + interceptors
│   │   ├── authService.js         # Auth endpoints
│   │   ├── bookService.js         # Book endpoints
│   │   ├── borrowService.js       # Borrow/return endpoints
│   │   └── adminService.js        # Admin endpoints
│   ├── utils/
│   │   ├── constants.js           # API endpoints, routes, roles
│   │   └── helpers.js             # Utility functions
│   └── App.jsx                    # Root component + routes
├── package.json
├── vite.config.js
├── tailwind.config.js
├── .env.example
└── README.md
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Copy the example file and set your backend URL:

```bash
copy .env.example .env   # Windows
cp .env.example .env     # Unix
```

**Environment Variables:**

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

## Available Pages

| Path | Description | Auth Required | Admin Only |
|---|---|---|---|
| `/login` | Login page | No | No |
| `/register` | Registration page | No | No |
| `/dashboard` | Member home | Yes | No |
| `/books` | Browse book catalog | Yes | No |
| `/books/:id` | Book detail page | Yes | No |
| `/borrowing-history` | Member borrowing history | Yes | No |
| `/profile` | View/edit profile | Yes | No |
| `/admin` | Admin dashboard | Yes | **Yes** |
| `/admin/users` | Manage users | Yes | **Yes** |
| `/admin/books` | Manage books | Yes | **Yes** |
| `/admin/borrowing-history` | All borrowing records | Yes | **Yes** |

## API Configuration

The base axios instance (`src/services/api.js`) automatically:

- Sets `baseURL` from `VITE_API_BASE_URL`
- Attaches `Authorization: Bearer <token>` from localStorage
- Handles 401 responses (clears session, redirects to login)
- Logs all errors via `window.dispatchEvent`

## Troubleshooting

### Backend not responding?

Verify the backend is running:

```bash
curl http://localhost:8000/health
```

### CORS error?

Check `CORS_ORIGINS` in `backend/.env` includes `http://localhost:5173`.

### Token expired?

Log out and log back in. The app clears the session automatically on 401.

### Page not loading?

Open the browser console (F12) and check for:
- Red error messages
- Network tab 4xx/5xx responses
- Missing environment variable configuration

## Build for Production

```bash
npm run build
```

Output is written to `dist/`. Serve it with any static host (Vercel, Netlify, Nginx, etc.).