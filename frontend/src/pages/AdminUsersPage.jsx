import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import LoadingSpinner from '../components/LoadingSpinner';
import { adminService } from '../services/adminService';
import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

const EMPTY_MEMBER_FORM = {
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  phone: '',
  address: '',
};

export default function AdminUsersPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [skip, setSkip] = useState(0);
  const [total, setTotal] = useState(0);
  const limit = 10;

  // Search & Filters
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');

  // Add Member Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState(EMPTY_MEMBER_FORM);
  const [formErrors, setFormErrors] = useState({});
  const [creating, setCreating] = useState(false);

  // Delete User Confirmation Modal
  const [deletingUser, setDeletingUser] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate(ROUTES.unauthorized);
      return;
    }
    loadUsers();
  }, [user, navigate, skip, search, roleFilter]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await adminService.getUsers(skip, limit, search, roleFilter);
      setUsers(data.items || []);
      setTotal(data.total || 0);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.message || err.userMessage || err.message || 'Failed to load library members');
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  const validateMemberForm = () => {
    const errs = {};
    if (!formData.first_name.trim()) errs.first_name = 'First name is required';
    if (!formData.last_name.trim()) errs.last_name = 'Last name is required';
    
    if (!formData.email.trim()) {
      errs.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
      errs.email = 'Please provide a valid email address';
    }

    if (!formData.password) {
      errs.password = 'Password is required';
    } else if (formData.password.length < 6) {
      errs.password = 'Password must be at least 6 characters long';
    }

    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleOpenAddModal = () => {
    setFormData(EMPTY_MEMBER_FORM);
    setFormErrors({});
    setShowAddModal(true);
  };

  const handleCreateMember = async (e) => {
    e.preventDefault();
    if (!validateMemberForm()) return;

    setCreating(true);
    setError(null);
    try {
      const payload = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        email: formData.email.trim(),
        password: formData.password,
        phone: formData.phone.trim() || undefined,
        address: formData.address.trim() || undefined,
      };

      await adminService.createMember(payload);
      setSuccess(`Member account for ${formData.first_name} ${formData.last_name} (${formData.email}) created successfully.`);
      setShowAddModal(false);
      setFormData(EMPTY_MEMBER_FORM);
      loadUsers();
      setTimeout(() => setSuccess(null), 4000);
    } catch (err) {
      const resp = err.response?.data;
      const msg = resp?.message || resp?.detail || err.userMessage || err.message || 'Failed to create member account';
      setFormErrors(prev => ({ ...prev, api: msg }));
    } finally {
      setCreating(false);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    try {
      await adminService.updateUserRole(userId, newRole);
      setSuccess(`User role changed to ${newRole.toUpperCase()}.`);
      loadUsers();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.response?.data?.message || err.userMessage || err.message || 'Failed to update user role');
      setTimeout(() => setError(null), 4000);
    }
  };

  const handleDeleteUser = async () => {
    if (!deletingUser) return;
    setDeleteBusy(true);
    try {
      await adminService.deleteUser(deletingUser.id);
      setSuccess(`Member account (${deletingUser.email}) removed successfully.`);
      setDeletingUser(null);
      loadUsers();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      const resp = err.response?.data;
      setError(resp?.message || err.userMessage || err.message || 'Failed to delete member account');
      setDeletingUser(null);
      setTimeout(() => setError(null), 4000);
    } finally {
      setDeleteBusy(false);
    }
  };

  return (
    <main className="page-container">
      {/* Page Header */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold text-brand-900">Manage Members & Access</h1>
          <p className="mt-1 text-sm text-ink-600">
            Administrative control center for registering library patrons, supervising roles, and managing credentials.
          </p>
        </div>
        <button
          type="button"
          onClick={handleOpenAddModal}
          className="btn-forest flex items-center gap-2 self-start sm:self-auto"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
          </svg>
          <span>Add New Member</span>
        </button>
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

      {/* Filter / Search Bar */}
      <div className="card mb-6 p-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label className="input-label" htmlFor="user-search-input">Search Members</label>
            <div className="relative">
              <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-ink-400">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </span>
              <input
                id="user-search-input"
                type="text"
                placeholder="Search by name or email…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setSkip(0);
                }}
                className="w-full rounded-lg border border-cream-300 py-2 pl-9 pr-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
          <div>
            <label className="input-label" htmlFor="user-role-filter">Filter by Role</label>
            <select
              id="user-role-filter"
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setSkip(0);
              }}
              className="w-full rounded-lg border border-cream-300 py-2 px-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">All Roles</option>
              <option value="member">Members Only</option>
              <option value="admin">Administrators Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Members Table */}
      {loading && users.length === 0 ? (
        <LoadingSpinner />
      ) : users.length > 0 ? (
        <div className="card overflow-hidden p-0 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-cream-300 bg-cream-50 text-xs font-semibold uppercase tracking-wider text-ink-600">
                  <th className="px-5 py-3.5">ID</th>
                  <th className="px-5 py-3.5">Member Name</th>
                  <th className="px-5 py-3.5">Email Address</th>
                  <th className="px-5 py-3.5">Assigned Role</th>
                  <th className="px-5 py-3.5">Contact / Address</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cream-200 text-sm">
                {users.map((u) => {
                  const isCurrentAdmin = u.id === user?.id;
                  const isUserAdmin = u.role === 'admin';
                  return (
                    <tr key={u.id} className="hover:bg-cream-50/60 transition-colors">
                      <td className="px-5 py-4 font-mono text-xs text-ink-500">#{u.id}</td>
                      <td className="px-5 py-4">
                        <div className="font-semibold text-ink-900">
                          {[u.first_name, u.last_name].filter(Boolean).join(' ') || 'Unnamed Member'}
                        </div>
                        {isCurrentAdmin && (
                          <span className="text-[10px] font-bold uppercase tracking-wider text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded">
                            You
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-4 font-mono text-xs text-ink-700">{u.email}</td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              isUserAdmin
                                ? 'bg-amber-100 text-amber-800 border border-amber-300'
                                : 'bg-forest-100 text-forest-800 border border-forest-300'
                            }`}
                          >
                            {u.role}
                          </span>
                          {!isCurrentAdmin && (
                            <select
                              value={u.role}
                              onChange={(e) => handleRoleChange(u.id, e.target.value)}
                              aria-label={`Change role for ${u.email}`}
                              className="rounded border border-cream-300 bg-white py-0.5 px-1.5 text-xs text-ink-700 hover:bg-cream-100 focus:outline-none"
                            >
                              <option value="member">member</option>
                              <option value="admin">admin</option>
                            </select>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-4 text-xs text-ink-500">
                        {u.phone || u.address ? (
                          <div>
                            {u.phone && <div>📞 {u.phone}</div>}
                            {u.address && <div className="truncate max-w-xs">📍 {u.address}</div>}
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="px-5 py-4 text-right">
                        {!isCurrentAdmin ? (
                          <button
                            type="button"
                            onClick={() => setDeletingUser(u)}
                            className="rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-100 transition-colors"
                          >
                            Delete
                          </button>
                        ) : (
                          <span className="text-xs text-ink-400 font-medium">Primary</span>
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
              <span className="font-semibold">{total}</span> members
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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          <h3 className="mt-3 text-base font-semibold text-ink-800">No members found</h3>
          <p className="mt-1 text-sm text-ink-500">Adjust your search parameters or register a new member account.</p>
          <button
            type="button"
            onClick={handleOpenAddModal}
            className="btn-forest mt-4"
          >
            Add Member
          </button>
        </div>
      )}

      {/* Add Member Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/60 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="relative w-full max-w-lg rounded-2xl border border-cream-300 bg-white p-6 shadow-elevation my-8">
            <div className="flex items-center justify-between border-b border-cream-200 pb-4 mb-4">
              <div>
                <h2 className="text-xl font-serif font-bold text-brand-900">
                  Register New Library Member
                </h2>
                <p className="text-xs text-ink-500 mt-0.5">
                  Only administrators can create member accounts.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="rounded-lg p-1 text-ink-400 hover:bg-cream-100 hover:text-ink-700"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {formErrors.api && (
              <div className="mb-4 rounded-lg border border-rose-300 bg-rose-50 p-3 text-xs font-medium text-rose-800">
                {formErrors.api}
              </div>
            )}

            <form onSubmit={handleCreateMember} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="input-label" htmlFor="member-first-name">First Name *</label>
                  <input
                    id="member-first-name"
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    placeholder="e.g. Eleanor"
                    className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                    required
                  />
                  {formErrors.first_name && <p className="mt-1 text-xs text-rose-600">{formErrors.first_name}</p>}
                </div>

                <div>
                  <label className="input-label" htmlFor="member-last-name">Last Name *</label>
                  <input
                    id="member-last-name"
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    placeholder="e.g. Vance"
                    className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                    required
                  />
                  {formErrors.last_name && <p className="mt-1 text-xs text-rose-600">{formErrors.last_name}</p>}
                </div>
              </div>

              <div>
                <label className="input-label" htmlFor="member-email">Email Address *</label>
                <input
                  id="member-email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="member@athenaeum.org"
                  className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                  required
                />
                {formErrors.email && <p className="mt-1 text-xs text-rose-600">{formErrors.email}</p>}
              </div>

              <div>
                <label className="input-label" htmlFor="member-password">Initial Password * (minimum 6 characters)</label>
                <input
                  id="member-password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                  required
                />
                {formErrors.password && <p className="mt-1 text-xs text-rose-600">{formErrors.password}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="input-label" htmlFor="member-phone">Phone Number (optional)</label>
                  <input
                    id="member-phone"
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+1 555-0199"
                    className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="input-label" htmlFor="member-address">Address (optional)</label>
                  <input
                    id="member-address"
                    type="text"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    placeholder="123 Library Way"
                    className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-cream-200">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="btn-forest"
                >
                  {creating ? 'Creating Member…' : 'Create Member Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-rose-200 bg-white p-6 shadow-elevation">
            <div className="flex items-center gap-3 text-rose-600 mb-3">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h3 className="text-lg font-bold text-ink-900">Remove Member Account</h3>
            </div>
            <p className="text-sm text-ink-600">
              Are you sure you want to remove account <span className="font-semibold text-ink-900">{deletingUser.email}</span>?
            </p>
            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeletingUser(null)}
                className="btn-secondary"
                disabled={deleteBusy}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteUser}
                disabled={deleteBusy}
                className="btn-danger"
              >
                {deleteBusy ? 'Removing…' : 'Remove Account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}