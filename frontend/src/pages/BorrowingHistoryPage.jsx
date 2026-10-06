/**
 * Borrowing history page.
 *
 * The borrowing endpoints are a later phase of the PRD, so this page states what
 * is coming instead of rendering an empty table that looks broken. The route and
 * its navigation entry exist now so the information architecture is settled.
 */

import { Link } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

/**
 * Render the borrowing history placeholder.
 *
 * @returns {JSX.Element} The page.
 */
export default function BorrowingHistoryPage() {
  const { user } = useAuth();

  return (
    <main className="page-container">
      <header className="mb-6">
        <h1 className="text-2xl">My borrowing history</h1>
        <p className="mt-1 text-sm text-ink-600">
          Loans, returns and outstanding fines for {user?.email ?? 'your account'}.
        </p>
      </header>

      <div className="card text-center">
        <h2 className="text-lg">Coming soon</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-ink-600">
          Borrowing records arrive with the borrowing endpoints. Nothing is wrong with your
          account - there simply are no loans to show yet.
        </p>
        <Link to={ROUTES.catalog} className="btn-primary mt-4">
          Browse the catalog
        </Link>
      </div>
    </main>
  );
}
