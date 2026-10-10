/**
 * Application routes.
 *
 * Public pages (login, register, 403, 404) sit outside the guard; everything
 * that needs a session is wrapped in `ProtectedRoute`, which also enforces the
 * admin-only route. The trailing `*` route renders `NotFoundPage`.
 */

import { Navigate, Route, Routes } from "react-router-dom";

import ErrorBoundary from "./components/ErrorBoundary";
import ApiEventBridge from "./components/ApiEventBridge";
import Header from "./components/Header";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import AdminBooksPage from "./pages/AdminBooksPage";
import AdminBorrowingHistoryPage from "./pages/AdminBorrowingHistoryPage";
import BookCatalogPage from "./pages/BookCatalogPage";
import BookDetailPage from "./pages/BookDetailPage";
import BorrowingHistoryPage from "./pages/BorrowingHistoryPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import UnauthorizedPage from "./pages/UnauthorizedPage";
import { ROUTES } from "./utils/constants";

/**
 * Render the application shell and its routes.
 *
 * @returns {JSX.Element} The app.
 */
export default function App() {
  return (
    <ErrorBoundary>
      <div className="app-shell">
        <ApiEventBridge />
        <Header />
        <Routes>
          <Route
            path={ROUTES.home}
            element={<Navigate to={ROUTES.dashboard} replace />}
          />
          <Route path={ROUTES.login} element={<LoginPage />} />
          <Route path={ROUTES.register} element={<RegisterPage />} />
          <Route path={ROUTES.unauthorized} element={<UnauthorizedPage />} />
          <Route
            path={ROUTES.adminDashboard}
            element={
              <ProtectedRoute requiredRole="admin">
                <AdminDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path={ROUTES.adminUsers}
            element={
              <ProtectedRoute requiredRole="admin">
                <AdminUsersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path={ROUTES.adminBooks}
            element={
              <ProtectedRoute requiredRole="admin">
                <AdminBooksPage />
              </ProtectedRoute>
            }
          />
          <Route
            path={ROUTES.adminBorrowingHistory}
            element={
              <ProtectedRoute>
                <AdminBorrowingHistoryPage />
              </ProtectedRoute>
            }
          />

          <Route
            path={ROUTES.dashboard}
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path={ROUTES.catalog}
            element={
              <ProtectedRoute>
                <BookCatalogPage />
              </ProtectedRoute>
            }
          />
          <Route
            path={ROUTES.bookDetail}
            element={
              <ProtectedRoute>
                <BookDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path={ROUTES.borrowingHistory}
            element={
              <ProtectedRoute>
                <BorrowingHistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path={ROUTES.profile}
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </div>
    </ErrorBoundary>
  );
}
