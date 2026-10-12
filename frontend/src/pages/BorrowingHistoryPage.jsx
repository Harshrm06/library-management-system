import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import LoadingSpinner from '../components/LoadingSpinner';
import borrowService from '../services/borrowService';
import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

export default function BorrowingHistoryPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [borrowings, setBorrowings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [skip, setSkip] = useState(0);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState('');
  const [returningId, setReturningId] = useState(null);
  const limit = 10;

  useEffect(() => {
    if (!user) {
      navigate(ROUTES.login);
      return;
    }
    if (user.role === 'admin') {
      navigate(ROUTES.adminDashboard, { replace: true });
      return;
    }
    loadHistory();
  }, [user, navigate, skip, status]);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const res = await borrowService.getMemberHistory(skip, limit, status);
      if (res.success) {
        const records = res.data?.records || res.records || [];
        setBorrowings(records);
        setTotal(res.data?.total || res.total || records.length);
        setError(null);
      } else {
        setError(res.message || 'Failed to load borrowing history');
        setBorrowings([]);
      }
    } catch (err) {
      setError(err.response?.data?.message || err.userMessage || err.message || 'Failed to load borrowing history');
      setBorrowings([]);
    } finally {
      setLoading(false);
    }
  };

  const handleReturnBook = async (borrowingId, bookTitle, fineAmount) => {
    const fineText = fineAmount > 0 ? ` (Accrued late fine: ₹${fineAmount.toFixed(2)})` : '';
    if (!window.confirm(`Return "${bookTitle}"${fineText}?`)) return;

    setReturningId(borrowingId);
    setError(null);
    try {
      const res = await borrowService.returnBook(borrowingId);
      if (res.success) {
        setSuccess(`"${bookTitle}" returned successfully.`);
        loadHistory();
        setTimeout(() => setSuccess(null), 3500);
      } else {
        setError(res.message || 'Failed to return book.');
      }
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Failed to return book.');
    } finally {
      setReturningId(null);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getStatusBadge = (recStatus) => {
    const normalized = String(recStatus || '').toUpperCase();
    switch (normalized) {
      case 'BORROWED':
        return (
          <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-semibold text-brand-800 border border-brand-200">
            On Loan
          </span>
        );
      case 'RETURNED':
        return (
          <span className="rounded-full bg-forest-50 px-2.5 py-0.5 text-xs font-semibold text-forest-800 border border-forest-300">
            Returned
          </span>
        );
      case 'OVERDUE':
        return (
          <span className="rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-800 border border-rose-300">
            Overdue
          </span>
        );
      default:
        return (
          <span className="rounded-full bg-cream-200 px-2.5 py-0.5 text-xs font-semibold text-ink-700">
            {recStatus}
          </span>
        );
    }
  };

  return (
    <main className="page-container">
      {/* Page Header */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold text-brand-900">My Borrowing History</h1>
          <p className="mt-1 text-sm text-ink-600">
            Review your historical loans, return active borrowings, and check due dates.
          </p>
        </div>
        <Link to={ROUTES.catalog} className="btn-primary self-start sm:self-auto">
          Browse Catalog
        </Link>
      </div>

      {/* Notifications */}
      {error && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800">
          <svg className="h-5 w-5 shrink-0 text-rose-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-sm font-medium">{error}</div>
        </div>
      )}

      {success && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-forest-300 bg-forest-50 p-4 text-forest-800">
          <svg className="h-5 w-5 shrink-0 text-forest-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-sm font-medium">{success}</div>
        </div>
      )}

      {/* Filter by Status */}
      <div className="card mb-6 p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <label className="text-xs font-semibold uppercase tracking-wider text-ink-600" htmlFor="status-filter">
              Filter by Status:
            </label>
            <select
              id="status-filter"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setSkip(0);
              }}
              className="rounded-lg border border-cream-300 bg-white px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none"
            >
              <option value="">All Records</option>
              <option value="BORROWED">Currently On Loan</option>
              <option value="RETURNED">Returned Volumes</option>
              <option value="OVERDUE">Overdue</option>
            </select>
          </div>
          <span className="text-xs text-ink-500">
            Total records: <span className="font-semibold text-ink-800">{total}</span>
          </span>
        </div>
      </div>

      {/* Borrowing Table */}
      {loading && borrowings.length === 0 ? (
        <LoadingSpinner />
      ) : borrowings.length > 0 ? (
        <div className="card overflow-hidden p-0 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-cream-300 bg-cream-50 text-xs font-semibold uppercase tracking-wider text-ink-600">
                  <th className="px-5 py-3.5">Book Title</th>
                  <th className="px-5 py-3.5">Issue Date</th>
                  <th className="px-5 py-3.5">Due Date</th>
                  <th className="px-5 py-3.5">Return Date</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Late Fine</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cream-200 text-sm">
                {borrowings.map((record) => {
                  const fine = Number(record.fine_amount) || 0;
                  const isBorrowed = String(record.status).toUpperCase() === 'BORROWED';
                  const title = record.book_title || record.book?.title || 'Book Title';

                  return (
                    <tr key={record.id} className="hover:bg-cream-50/60 transition-colors">
                      <td className="px-5 py-4 font-semibold text-ink-900">
                        {title}
                      </td>
                      <td className="px-5 py-4 text-xs text-ink-600">
                        {formatDate(record.issue_date || record.borrow_date)}
                      </td>
                      <td className="px-5 py-4 text-xs font-medium text-brand-900">
                        {formatDate(record.due_date)}
                      </td>
                      <td className="px-5 py-4 text-xs text-ink-500">
                        {formatDate(record.return_date)}
                      </td>
                      <td className="px-5 py-4">
                        {getStatusBadge(record.status)}
                      </td>
                      <td className="px-5 py-4 font-mono text-xs">
                        <span className={fine > 0 ? 'text-rose-600 font-semibold' : 'text-ink-600'}>
                          ₹{fine.toFixed(2)}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right">
                        {isBorrowed ? (
                          <button
                            type="button"
                            onClick={() => handleReturnBook(record.id, title, fine)}
                            disabled={returningId === record.id}
                            className="rounded-lg bg-forest-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-forest-700 disabled:opacity-50 transition-colors"
                          >
                            {returningId === record.id ? 'Returning…' : 'Return Book'}
                          </button>
                        ) : (
                          <span className="text-xs text-ink-400 font-medium">Completed</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex flex-col sm:flex-row items-center justify-between border-t border-cream-300 px-5 py-3.5 gap-3 bg-cream-50/50">
            <span className="text-xs text-ink-600">
              Showing <span className="font-semibold">{total > 0 ? skip + 1 : 0}</span> to{' '}
              <span className="font-semibold">{Math.min(skip + limit, total)}</span> of{' '}
              <span className="font-semibold">{total}</span> records
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setSkip(Math.max(0, skip - limit))}
                disabled={skip === 0}
                className="btn-secondary py-1.5 px-3 text-xs"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => skip + limit < total && setSkip(skip + limit)}
                disabled={skip + limit >= total}
                className="btn-secondary py-1.5 px-3 text-xs"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="card text-center py-12">
          <svg className="mx-auto h-12 w-12 text-ink-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <h3 className="mt-3 text-base font-semibold text-ink-800">No borrowing records found</h3>
          <p className="mt-1 text-sm text-ink-500">
            {status ? 'No records match the selected status filter.' : 'You have not borrowed any books yet.'}
          </p>
          <div className="mt-4">
            <Link to={ROUTES.catalog} className="btn-primary">
              Browse Books
            </Link>
          </div>
        </div>
      )}
    </main>
  );
}