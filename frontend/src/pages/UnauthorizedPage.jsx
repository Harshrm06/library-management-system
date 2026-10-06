/**
 * Shown when a signed-in user lacks the role a route requires.
 */

import { Link } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

/**
 * Render the 403 screen.
 *
 * @returns {JSX.Element} The page.
 */
export default function UnauthorizedPage() {
  const { user } = useAuth();

  return (
    <main className="page-container flex flex-col items-center justify-center text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-brand-600">403</p>
      <h1 className="mt-2 text-3xl">You do not have access</h1>
      <p className="mt-2 max-w-md text-ink-600">
        {user
          ? `This area is restricted. Your account is signed in as "${user.role}".`
          : 'This area is restricted.'}
      </p>
      <Link to={ROUTES.catalog} className="btn-primary mt-6">
        Back to the catalog
      </Link>
    </main>
  );
}
