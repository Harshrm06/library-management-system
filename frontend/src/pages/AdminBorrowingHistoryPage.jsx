import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import LoadingSpinner from '../components/LoadingSpinner';
import { adminService } from '../services/adminService';
import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';


export default function AdminBorrowingHistoryPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [borrowings, setBorrowings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [skip, setSkip] = useState(0);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const limit = 10;

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate(ROUTES.unauthorized);
      return;
    }

    loadBorrowings();
  }, [user, navigate, skip, status, startDate, endDate]);

  const loadBorrowings = async () => {
    try {
      setLoading(true);
      const filters = {};
      if (status) filters.status = status;
      if (startDate) filters.start_date = startDate;
      if (endDate) filters.end_date = endDate;

      const data = await adminService.getBorrowingHistory(skip, limit, filters);
      setBorrowings(data.items || []);
      setTotal(data.total || 0);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load borrowing history');
      setBorrowings([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString();
  };

  const getStatusBadgeColor = (status) => {
    switch (status) {
      case 'BORROWED':
        return 'bg-blue-100 text-blue-800';
      case 'RETURNED':
        return 'bg-green-100 text-green-800';
      case 'OVERDUE':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getFineColor = (fine) => {
    return fine > 0 ? 'text-red-600 font-semibold' : 'text-green-600';
  };

  if (loading && borrowings.length === 0) return <LoadingSpinner />;

  return (
    <div>
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">Borrowing History (All Members)</h1>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6 bg-white p-4 rounded-lg shadow">
          <div>
            <label className="block text-sm font-semibold mb-2">Status</label>
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setSkip(0);
              }}
              className="w-full px-4 py-2 border rounded"
            >
              <option value="">All Statuses</option>
              <option value="BORROWED">Borrowed</option>
              <option value="RETURNED">Returned</option>
              <option value="OVERDUE">Overdue</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-2">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value);
                setSkip(0);
              }}
              className="w-full px-4 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-2">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value);
                setSkip(0);
              }}
              className="w-full px-4 py-2 border rounded"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={() => {
                setStatus('');
                setStartDate('');
                setEndDate('');
                setSkip(0);
              }}
              className="w-full bg-gray-400 hover:bg-gray-500 text-white px-4 py-2 rounded"
            >
              Clear Filters
            </button>
          </div>
        </div>

        {/* Borrowing Table */}
        {borrowings.length > 0 ? (
          <>
            <div className="overflow-x-auto bg-white rounded-lg shadow">
              <table className="w-full">
                <thead className="bg-gray-100 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Member Email</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Book Title</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Borrow Date</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Due Date</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Return Date</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Status</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Fine (₹)</th>
                  </tr>
                </thead>
                <tbody>
                  {borrowings.map((record) => (
                    <tr key={record.id} className="border-b hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm">{record.user_email || record.user?.email || 'N/A'}</td>
                      <td className="px-6 py-4 text-sm font-medium">{record.book_title || record.book?.title || 'N/A'}</td>
                      <td className="px-6 py-4 text-sm">{formatDate(record.borrow_date)}</td>
                      <td className="px-6 py-4 text-sm">{formatDate(record.due_date)}</td>
                      <td className="px-6 py-4 text-sm">{formatDate(record.return_date)}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusBadgeColor(record.status)}`}>
                          {record.status}
                        </span>
                      </td>
                      <td className={`px-6 py-4 text-sm ${getFineColor(record.fine_amount || 0)}`}>
                        ₹{(Number(record.fine_amount) || 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex justify-between items-center mt-6">
              <button
                onClick={() => setSkip(Math.max(0, skip - limit))}
                disabled={skip === 0}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Showing {skip + 1}-{Math.min(skip + limit, total)} of {total}
              </span>
              <button
                onClick={() => skip + limit < total && setSkip(skip + limit)}
                disabled={skip + limit >= total}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded"
              >
                Next
              </button>
            </div>
          </>
        ) : (
          <p className="text-gray-600 bg-white p-6 rounded-lg">No borrowing records found</p>
        )}
      </div>
    </div>
  );
}