/**
 * Account Registration Guard / Informational Page.
 *
 * In accordance with Phase 5 policy:
 * - Public self-registration is restricted: accounts are created by administrators.
 * - Authenticated admins accessing this route are directed to the administrative "Manage Members" section.
 * - Members or public visitors are informed that library cards are issued by administrators.
 */

import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

export default function RegisterPage() {
  const { isAuthenticated, isAdmin } = useAuth();

  // If authenticated as admin, guide directly to Admin Member Management
  if (isAuthenticated && isAdmin) {
    return <Navigate to={ROUTES.adminUsers} replace />;
  }

  // If authenticated as member, redirect to Dashboard
  if (isAuthenticated && !isAdmin) {
    return <Navigate to={ROUTES.dashboard} replace />;
  }

  // Unauthenticated visitor notice
  return (
    <main className="page-container flex min-h-[75vh] items-center justify-center py-12">
      <div className="mx-auto w-full max-w-md">
        <div className="card text-center border-cream-300 bg-white p-8 shadow-elevation rounded-2xl">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-800">
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>

          <h1 className="mt-4 font-serif text-2xl font-bold text-brand-950">
            Admin-Managed Registration
          </h1>
          <p className="mt-2 text-sm text-ink-600 leading-relaxed">
            Public self-registration is restricted. In this library management system, member accounts are provisioned exclusively by authorized administrators.
          </p>

          <div className="mt-4 rounded-xl bg-cream-50 p-4 border border-cream-200 text-xs text-ink-600 text-left">
            <p className="font-semibold text-ink-800">How to obtain access:</p>
            <ul className="mt-1.5 list-disc space-y-1 pl-4">
              <li>Contact the library circulation desk or administrator.</li>
              <li>Administrators can create accounts via the <strong>Manage Members</strong> portal.</li>
            </ul>
          </div>

          <div className="mt-6 flex flex-col gap-2.5">
            <Link to={ROUTES.login} className="btn-primary w-full text-center">
              Sign In to Existing Account
            </Link>
            <Link to={ROUTES.catalog} className="btn-secondary w-full text-center">
              Browse Public Catalog
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
