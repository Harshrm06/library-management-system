/**
 * Fallback page for unknown routes.
 */

import { Link } from 'react-router-dom';

import { ROUTES } from '../utils/constants';

/**
 * Render the 404 screen.
 *
 * @returns {JSX.Element} The page.
 */
export default function NotFoundPage() {
  return (
    <main className="page-container flex flex-col items-center justify-center text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-brand-600">404</p>
      <h1 className="mt-2 text-3xl">Page not found</h1>
      <p className="mt-2 max-w-md text-ink-600">
        The page you are looking for does not exist or may have been moved.
      </p>
      <Link to={ROUTES.catalog} className="btn-primary mt-6">
        Go to the catalog
      </Link>
    </main>
  );
}
