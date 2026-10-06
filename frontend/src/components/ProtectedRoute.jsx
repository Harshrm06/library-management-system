/**
 * Route guard: requires a session and, optionally, a specific role.
 *
 * Works in two modes:
 *
 * * as a layout route - `<Route element={<ProtectedRoute />}>` - where it renders
 *   the nested `<Outlet />`;
 * * as a wrapper - `<ProtectedRoute requiredRole="admin"><Page /></ProtectedRoute>`
 *   - where it renders `children`.
 *
 * An anonymous visitor is redirected to the login page with the attempted
 * location attached, so `LoginPage` can send them back there after signing in.
 * A signed-in visitor with the wrong role gets the 403 screen instead of a
 * redirect loop.
 *
 * @example
 * <Route
 *   path="/admin"
 *   element={
 *     <ProtectedRoute requiredRole="admin">
 *       <AdminDashboardPage />
 *     </ProtectedRoute>
 *   }
 * />
 */

import { Navigate, Outlet, useLocation } from 'react-router-dom';

import LoadingSpinner from './LoadingSpinner';
import UnauthorizedPage from '../pages/UnauthorizedPage';
import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

/**
 * Guard a route or a subtree.
 *
 * @param {{
 *   children?: React.ReactNode,
 *   requiredRole?: 'admin' | 'member',
 *   fallback?: React.ReactNode,
 *   redirectTo?: string,
 * }} props Component props.
 * @returns {JSX.Element} The protected content, a loading state, the 403 page,
 *   or a redirect to the login page.
 */
export default function ProtectedRoute({
  children,
  requiredRole,
  fallback = null,
  redirectTo = ROUTES.login,
}) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  // The session is still being restored from storage: show the fallback rather
  // than bouncing a signed-in user to the login page.
  if (loading && !isAuthenticated) {
    return (
      fallback ?? <LoadingSpinner fullScreen label="Restoring your session…" />
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={redirectTo} replace state={{ from: location }} />;
  }

  // Role check is case-insensitive so "Admin" and "admin" behave the same.
  if (requiredRole && String(user?.role ?? '').toLowerCase() !== requiredRole.toLowerCase()) {
    return <UnauthorizedPage />;
  }

  return children ?? <Outlet />;
}
