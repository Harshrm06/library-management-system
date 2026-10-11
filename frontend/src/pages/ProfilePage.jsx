import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import LoadingSpinner from "../components/LoadingSpinner";
import authService from "../services/authService";
import { useAuth } from "../hooks/useAuth";
import { ROUTES } from "../utils/constants";
import { formatDate } from "../utils/helpers";

export default function ProfilePage() {
  const navigate = useNavigate();
  const { user, setUser, updateUser, isAdmin } = useAuth();
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    address: "",
  });

  useEffect(() => {
    if (!user) {
      navigate(ROUTES.login);
      return;
    }

    setFormData({
      first_name: user.first_name || user.name || "",
      last_name: user.last_name || "",
      phone: user.phone || "",
      address: user.address || "",
    });
  }, [user, navigate]);

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();

    if (!formData.first_name.trim()) {
      setError("First name is required");
      return;
    }

    try {
      setLoading(true);
      const updateData = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        phone: formData.phone.trim() || undefined,
        address: formData.address.trim() || undefined,
      };
      const response = await authService.updateProfile(updateData);

      if (response.success) {
        const updatedUser = response.data?.user || response.data;
        if (updatedUser) {
          if (updateUser) updateUser(updatedUser);
          else if (setUser) setUser(updatedUser);
        }
        setSuccess("Profile information updated successfully.");
        setEditing(false);
        setError(null);
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(response.message || "Failed to update profile");
      }
    } catch (err) {
      setError(err.response?.data?.message || err.message || "Failed to update profile");
    } finally {
      setLoading(false);
    }
  };

  if (!user) return <LoadingSpinner />;

  const displayName = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email;

  return (
    <main className="page-container max-w-2xl py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-serif font-bold text-brand-900">Patron Card Profile</h1>
        <p className="mt-1 text-sm text-ink-600">
          Personal identification, circulation preferences, and library account credentials.
        </p>
      </div>

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

      {!editing ? (
        <div className="card shadow-elevation rounded-2xl p-6 sm:p-8">
          <div className="flex items-start justify-between border-b border-cream-200 pb-5 mb-5">
            <div>
              <h2 className="text-xl font-serif font-bold text-ink-900">{displayName}</h2>
              <p className="font-mono text-xs text-ink-500 mt-0.5">{user.email}</p>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider ${
                isAdmin
                  ? "bg-amber-100 text-amber-800 border border-amber-300"
                  : "bg-forest-100 text-forest-800 border border-forest-300"
              }`}
            >
              {user.role}
            </span>
          </div>

          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-6">
            <div>
              <dt className="input-label">First Name</dt>
              <dd className="text-sm font-medium text-ink-800">{user.first_name || "—"}</dd>
            </div>
            <div>
              <dt className="input-label">Last Name</dt>
              <dd className="text-sm font-medium text-ink-800">{user.last_name || "—"}</dd>
            </div>
            <div>
              <dt className="input-label">Phone Contact</dt>
              <dd className="text-sm font-medium text-ink-800">{user.phone || "—"}</dd>
            </div>
            <div>
              <dt className="input-label">Card Issued</dt>
              <dd className="text-sm font-medium text-ink-800">{formatDate(user.created_at)}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="input-label">Postal Address</dt>
              <dd className="text-sm font-medium text-ink-800">{user.address || "—"}</dd>
            </div>
          </dl>

          <div className="pt-4 border-t border-cream-200 flex justify-end">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="btn-primary"
            >
              Edit Profile Details
            </button>
          </div>
        </div>
      ) : (
        <div className="card shadow-elevation rounded-2xl p-6 sm:p-8">
          <h2 className="text-lg font-serif font-bold text-ink-900 mb-4">Edit Profile Information</h2>
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div>
              <label className="input-label">Email Address (Fixed)</label>
              <input
                type="email"
                value={user.email}
                disabled
                className="w-full rounded-lg border border-cream-200 bg-cream-100 px-3 py-2 text-sm text-ink-500 font-mono cursor-not-allowed"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="input-label" htmlFor="profile-first-name">First Name *</label>
                <input
                  id="profile-first-name"
                  type="text"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleFormChange}
                  required
                  className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="input-label" htmlFor="profile-last-name">Last Name</label>
                <input
                  id="profile-last-name"
                  type="text"
                  name="last_name"
                  value={formData.last_name}
                  onChange={handleFormChange}
                  className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="input-label" htmlFor="profile-phone">Phone Number</label>
              <input
                id="profile-phone"
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleFormChange}
                className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="input-label" htmlFor="profile-address">Address</label>
              <textarea
                id="profile-address"
                name="address"
                rows="3"
                value={formData.address}
                onChange={handleFormChange}
                className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
            </div>

            <div className="pt-4 border-t border-cream-200 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary"
              >
                {loading ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}
