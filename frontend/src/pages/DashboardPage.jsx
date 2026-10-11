/**
 * Member landing dashboard.
 *
 * Provides a modern, library-themed overview for authenticated members:
 * displays their profile details, active book loans, and quick navigation into the catalog.
 * Strict Phase 5 compliance: No member creation controls exist here.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import FormError from '../components/FormError';
import LoadingSpinner from '../components/LoadingSpinner';
import { useAuth } from '../hooks/useAuth';
import borrowService from '../services/borrowService';
import { formatDate } from '../utils/helpers';
import { ROUTES } from '../utils/constants';

export default function DashboardPage() {
  const { user, error, isAdmin } = useAuth();

  const [activeLoans, setActiveLoans] = useState([]);
  const [loadingLoans, setLoadingLoans] = useState(true);
  const [returningId, setReturningId] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);
  const [actionError, setActionError] = useState(null);

  useEffect(() => {
    loadActiveLoans();
  }, []);

  const loadActiveLoans = async () => {
    try {
      setLoadingLoans(true);
      const res = await borrowService.getMemberHistory(0, 10, 'BORROWED');
      if (res.success) {
        const records = res.data?.records || [];
        setActiveLoans(records);
      }
    } catch {
      setActiveLoans([]);
    } finally {
      setLoadingLoans(false);
    }
  };

  const handleReturnBook = async (record) => {
    const bookTitle = record.book_title || record.book?.title || 'this title';
    if (!window.confirm(`Return "${bookTitle}" to the library?`)) return;

    setReturningId(record.id);
    setActionError(null);
    try {
      const res = await borrowService.returnBook(record.id);
      if (res.success) {
        setActionSuccess(`"${bookTitle}" returned successfully.`);
        loadActiveLoans();
        setTimeout(() => setActionSuccess(null), 3500);
      } else {
        setActionError(res.message || 'Failed to return book.');
        setTimeout(() => setActionError(null), 4000);
      }
    } catch (err) {
      setActionError(err.response?.data?.message || err.message || 'Error processing return.');
      setTimeout(() => setActionError(null), 4000);
    } finally {
      setReturningId(null);
    }
  };

  const displayName =
    [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.email || 'Member';

  return (
    <main className="page-container">
      {/* Welcome Banner */}
      <div className="mb-8 rounded-2xl border border-cream-300 bg-gradient-to-r from-brand-900 to-brand-800 p-6 sm:p-8 text-white shadow-elevation">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-cream-200 backdrop-blur-sm">
              <span>{user?.role === 'admin' ? 'Administrator Account' : 'Library Patron'}</span>
            </div>
            <h1 className="mt-3 font-serif text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Welcome back, {user?.first_name || displayName}
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-cream-200">
              Explore thousands of volumes in our collection, track your active reading loans, and manage your library card.
            </p>
          </div>

          <div className="flex flex-wrap gap-2.5">
            <Link
              to={ROUTES.catalog}
              className="inline-flex items-center gap-2 rounded-xl bg-forest-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-forest-700 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              <span>Explore Catalog</span>
            </Link>
            {isAdmin && (
              <Link
                to={ROUTES.adminDashboard}
                className="inline-flex items-center gap-2 rounded-xl bg-white/15 px-5 py-2.5 text-sm font-semibold text-white backdrop-blur-sm hover:bg-white/25 transition-colors border border-white/20"
              >
                <span>Admin Hub →</span>
              </Link>
            )}
          </div>
        </div>
      </div>

      <FormError message={error} />

      {actionSuccess && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-forest-300 bg-forest-50 p-4 text-forest-800">
          <svg className="h-5 w-5 shrink-0 text-forest-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-sm font-medium">{actionSuccess}</div>
        </div>
      )}

      {actionError && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800">
          <svg className="h-5 w-5 shrink-0 text-rose-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-sm font-medium">{actionError}</div>
        </div>
      )}

      {/* Account Info Cards */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">Patron Name</p>
          <p className="mt-1.5 text-lg font-bold text-ink-900">{displayName}</p>
        </div>
        <div className="card p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">Cardholder Email</p>
          <p className="mt-1.5 truncate text-lg font-bold text-ink-900">{user?.email ?? '—'}</p>
        </div>
        <div className="card p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">Role Status</p>
          <div className="mt-1.5 flex items-center gap-2">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider ${
                isAdmin
                  ? 'bg-amber-100 text-amber-800 border border-amber-300'
                  : 'bg-forest-100 text-forest-800 border border-forest-300'
              }`}
            >
              {user?.role ?? 'Member'}
            </span>
          </div>
        </div>
        <div className="card p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">Member Since</p>
          <p className="mt-1.5 text-lg font-bold text-ink-900">{formatDate(user?.created_at)}</p>
        </div>
      </div>

      {/* Active Loans Section */}
      <section className="mb-8" aria-labelledby="active-loans-heading">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 id="active-loans-heading" className="text-xl font-serif font-bold text-brand-900">
              Active Book Loans
            </h2>
            <span className="rounded-full bg-brand-100 px-2.5 py-0.5 text-xs font-bold text-brand-800">
              {activeLoans.length}
            </span>
          </div>
          <Link
            to={ROUTES.borrowingHistory}
            className="text-xs font-semibold text-brand-700 hover:text-brand-900 no-underline hover:underline"
          >
            View Complete Loan History →
          </Link>
        </div>

        {loadingLoans ? (
          <div className="card py-8 text-center"><LoadingSpinner /></div>
        ) : activeLoans.length > 0 ? (
          <div className="card overflow-hidden p-0 shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-cream-300 bg-cream-50 text-xs font-semibold uppercase tracking-wider text-ink-600">
                    <th className="px-5 py-3.5">Title</th>
                    <th className="px-5 py-3.5">Borrowed On</th>
                    <th className="px-5 py-3.5">Due Date</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cream-200 text-sm">
                  {activeLoans.map((loan) => (
                    <tr key={loan.id} className="hover:bg-cream-50/60 transition-colors">
                      <td className="px-5 py-4 font-semibold text-ink-900">
                        {loan.book_title || loan.book?.title || 'Book Title'}
                      </td>
                      <td className="px-5 py-4 text-ink-600">
                        {formatDate(loan.issue_date || loan.borrow_date)}
                      </td>
                      <td className="px-5 py-4 font-medium text-amber-800">
                        {formatDate(loan.due_date)}
                      </td>
                      <td className="px-5 py-4">
                        <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-semibold text-brand-700 border border-brand-200">
                          {loan.status}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right">
                        <button
                          type="button"
                          onClick={() => handleReturnBook(loan)}
                          disabled={returningId === loan.id}
                          className="rounded-lg bg-forest-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-forest-700 disabled:opacity-50 transition-colors"
                        >
                          {returningId === loan.id ? 'Returning…' : 'Return Book'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="card py-10 text-center">
            <svg className="mx-auto h-12 w-12 text-ink-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <h3 className="mt-3 text-base font-semibold text-ink-800">No books currently on loan</h3>
            <p className="mt-1 text-sm text-ink-500">
              Browse our catalog to select your next read.
            </p>
            <div className="mt-4">
              <Link to={ROUTES.catalog} className="btn-primary">
                Browse Books
              </Link>
            </div>
          </div>
        )}
      </section>

      {/* Quick Links */}
      <div className="flex flex-wrap gap-3">
        <Link to={ROUTES.catalog} className="btn-primary">
          Browse Book Catalog
        </Link>
        <Link to={ROUTES.borrowingHistory} className="btn-secondary">
          My Borrowing History
        </Link>
        <Link to={ROUTES.profile} className="btn-secondary">
          Manage Profile
        </Link>
      </div>
    </main>
  );
}
