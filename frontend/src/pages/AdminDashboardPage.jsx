import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
        setError(err.message || 'Failed to load dashboard stats');
        setStats(null);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, [user, navigate]);

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">Admin Dashboard</h1>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {stats && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {/* Total Books */}
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-gray-600 text-sm font-semibold mb-2">Total Books</h3>
                <p className="text-4xl font-bold text-blue-600">{stats.total_books || 0}</p>
              </div>

              {/* Total Members */}
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-gray-600 text-sm font-semibold mb-2">Total Members</h3>
                <p className="text-4xl font-bold text-green-600">{stats.total_members || 0}</p>
              </div>

              {/* Borrowed Books */}
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-gray-600 text-sm font-semibold mb-2">Currently Borrowed</h3>
                <p className="text-4xl font-bold text-orange-600">{stats.borrowed_books || 0}</p>
              </div>

              {/* Overdue Books */}
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-gray-600 text-sm font-semibold mb-2">Overdue Books</h3>
                <p className="text-4xl font-bold text-red-600">{stats.overdue_books || 0}</p>
              </div>
            </div>

            {/* Navigation Links */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                onClick={() => navigate(ROUTES.adminUsers)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold"
              >
                Manage Users
              </button>
              <button
                onClick={() => navigate(ROUTES.adminBooks)}
                className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-semibold"
              >
                Manage Books
              </button>
              <button
                onClick={() => navigate(ROUTES.adminBorrowingHistory)}
                className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-semibold"
              >
                Borrowing History
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}