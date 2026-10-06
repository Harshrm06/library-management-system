/**
 * Admin dashboard.
 *
 * Statistics come from `GET /api/admin/dashboard` in a later phase, so this page
 * is a placeholder - but it is a *real* admin-only route: reaching it as a
 * member renders the 403 screen through `ProtectedRoute`, which is what the role
 * check is for.
 */

import { Link } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

/**
 * Render the admin dashboard placeholder.
 *
 * @returns {JSX.Element} The page.
 */
export default function AdminDashboardPage() {
  const { user } = useAuth();

  return (
    <main className="page-container">
      <header className="mb-6">
        <h1 className="text-2xl">Admin dashboard</h1>
        <p className="mt-1 text-sm text-ink-600">
          Library statistics, inventory and user management for {user?.email ?? 'administrators'}.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {['Total books', 'Registered members', 'Books on loan', 'Overdue loans'].map((label) => (
          <div key={label} className="card">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</p>
            <p className="mt-1 text-3xl font-semibold text-ink-400">—</p>
            <p className="mt-1 text-xs text-ink-500">awaiting the admin API</p>
          </div>
        ))}
      </div>

      <div className="card mt-6">
        <h2 className="text-lg">Coming soon</h2>
        <p className="mt-2 text-sm text-ink-600">
          These cards fill in automatically once <code>GET /api/admin/dashboard</code> is available.
        </p>
        <Link to={ROUTES.catalog} className="btn-secondary mt-4">
          Back to the catalog
        </Link>
      </div>
    </main>
  );
}
