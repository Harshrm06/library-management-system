import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import LoadingSpinner from '../components/LoadingSpinner';
import { adminService } from '../services/adminService';
import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate(ROUTES.unauthorized);
      return;
    }

    const loadStats = async () => {
      try {
        setLoading(true);
        const data = await adminService.getDashboardStats();
        setStats(data);
        setError(null);
      } catch (err) {
        setError(err.response?.data?.message || err.userMessage || err.message || 'Failed to load dashboard metrics');
        setStats(null);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, [user, navigate]);

  if (loading) return <LoadingSpinner />;

  return (
    <main className="page-container">
      {/* Page Header */}
      <div className="mb-8 rounded-2xl border border-cream-300 bg-gradient-to-r from-brand-950 via-brand-900 to-brand-800 p-6 sm:p-8 text-white shadow-elevation">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-amber-500/20 border border-amber-400/30 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-amber-300">
              <span>Library Administration Console</span>
            </div>
            <h1 className="mt-3 font-serif text-3xl font-bold tracking-tight text-white sm:text-4xl">
              System Operations Hub
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-cream-200">
              Live circulation statistics, catalog inventory controls, and member access management.
            </p>
          </div>

          <div className="flex flex-wrap gap-2.5">
            <Link
              to={ROUTES.adminBooks}
              className="inline-flex items-center gap-2 rounded-xl bg-forest-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-forest-700 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
              </svg>
              <span>Manage Books</span>
            </Link>
            <Link
              to={ROUTES.adminUsers}
              className="inline-flex items-center gap-2 rounded-xl bg-white/15 px-5 py-2.5 text-sm font-semibold text-white backdrop-blur-sm hover:bg-white/25 transition-colors border border-white/20"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
              <span>Manage Members</span>
            </Link>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800">
          <svg className="h-5 w-5 shrink-0 text-rose-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-sm font-medium">{error}</div>
        </div>
      )}

      {stats && (
        <>
          {/* Key Metrics Cards */}
          <div className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {/* Total Books */}
            <div className="card border-l-4 border-l-brand-600 p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">Catalog Titles</p>
                <div className="rounded-lg bg-brand-50 p-2 text-brand-700">
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
              </div>
              <p className="mt-2 text-3xl font-bold font-serif text-brand-900">{stats.total_books || 0}</p>
              <p className="mt-1 text-xs text-ink-500">Active volumes in database</p>
            </div>

            {/* Total Members */}
            <div className="card border-l-4 border-l-forest-600 p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">Registered Members</p>
                <div className="rounded-lg bg-forest-50 p-2 text-forest-700">
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
              </div>
              <p className="mt-2 text-3xl font-bold font-serif text-forest-800">{stats.total_members || 0}</p>
              <p className="mt-1 text-xs text-ink-500">Patron accounts registered</p>
            </div>

            {/* Active Borrowed Books */}
            <div className="card border-l-4 border-l-amber-500 p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">Currently On Loan</p>
                <div className="rounded-lg bg-amber-50 p-2 text-amber-700">
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
              <p className="mt-2 text-3xl font-bold font-serif text-amber-700">{stats.borrowed_books || 0}</p>
              <p className="mt-1 text-xs text-ink-500">Books checked out</p>
            </div>

            {/* Overdue Books */}
            <div className="card border-l-4 border-l-rose-500 p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">Overdue Returns</p>
                <div className="rounded-lg bg-rose-50 p-2 text-rose-700">
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <p className="mt-2 text-3xl font-bold font-serif text-rose-700">{stats.overdue_books || 0}</p>
              <p className="mt-1 text-xs text-ink-500">Subject to late fines</p>
            </div>
          </div>

          {/* Quick Action Navigation Grid */}
          <h2 className="mb-4 text-xl font-serif font-bold text-brand-900">Administrative Actions</h2>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 mb-8">
            {/* Manage Books */}
            <div className="card hover:shadow-card-hover transition-all">
              <div className="flex items-center gap-3 mb-3">
                <div className="rounded-xl bg-forest-100 p-3 text-forest-800">
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-base font-bold text-ink-900">Manage Books</h3>
                  <p className="text-xs text-ink-500">Add, edit, adjust inventory & remove titles</p>
                </div>
              </div>
              <p className="text-sm text-ink-600 mb-4">
                Maintain collection quantities, update ISBN metadata, and verify copies available on shelf.
              </p>
              <Link to={ROUTES.adminBooks} className="btn-forest w-full text-center">
                Open Book Inventory →
              </Link>
            </div>

            {/* Manage Members */}
            <div className="card hover:shadow-card-hover transition-all">
              <div className="flex items-center gap-3 mb-3">
                <div className="rounded-xl bg-brand-100 p-3 text-brand-800">
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-base font-bold text-ink-900">Manage Members</h3>
                  <p className="text-xs text-ink-500">Register patrons & manage roles</p>
                </div>
              </div>
              <p className="text-sm text-ink-600 mb-4">
                Strict administrative member creation. Register new patrons with password hashing and assigned permissions.
              </p>
              <Link to={ROUTES.adminUsers} className="btn-primary w-full text-center">
                Open Member Management →
              </Link>
            </div>
          </div>
        </>
      )}
    </main>
  );
}