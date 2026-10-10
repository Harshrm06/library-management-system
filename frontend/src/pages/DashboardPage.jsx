/**
 * Member landing page.
 *
 * This is where a successful sign-in lands. The PRD reserves statistics for the
 * admin dashboard of a later phase, so today the page shows the signed-in
 * member's details and a way into the catalog; admin-only statistics will be
 * added when `GET /api/admin/dashboard` exists.
 */

import { Link } from "react-router-dom";

import FormError from "../components/FormError";
import { useAuth } from "../hooks/useAuth";
import { formatDate } from "../utils/helpers";
import { ROUTES } from "../utils/constants";
import { useNavigate } from "react-router-dom";

/**
 * Render the dashboard for the current member.
 *
 * @returns {JSX.Element} The page.
 */
export default function DashboardPage() {
  const { user, error } = useAuth();
  const navigate = useNavigate();

  console.log("ROUTES.register:", ROUTES.register);

  return (
    <main className="page-container">
      <header className="mb-6">
        <h1 className="text-2xl">
          Welcome back{user?.first_name ? `, ${user.first_name}` : ""}
        </h1>
        <p className="mt-1 text-sm text-ink-600">
          Here is your account summary. Loans and statistics arrive in a later
          phase.
        </p>
      </header>

      <FormError message={error} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-500">
            Name
          </p>
          <p className="mt-1 text-lg font-semibold">
            {user ? `${user.first_name} ${user.last_name}` : "—"}
          </p>
        </div>
        <div className="card">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-500">
            Email
          </p>
          <p className="mt-1 truncate text-lg font-semibold">
            {user?.email ?? "—"}
          </p>
        </div>
        <div className="card">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-500">
            Role
          </p>
          <p className="mt-1 text-lg font-semibold capitalize">
            {user?.role ?? "—"}
          </p>
        </div>
        <div className="card">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-500">
            Member since
          </p>
          <p className="mt-1 text-lg font-semibold">
            {formatDate(user?.created_at)}
          </p>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link to={ROUTES.catalog} className="btn-primary">
          Browse the catalog
        </Link>
        <button
          type="button"
          onClick={() => navigate(ROUTES.register)}
          className="btn-secondary"
        >
          Add another member
        </button>
      </div>
    </main>
  );
}
