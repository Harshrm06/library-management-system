import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import LoadingSpinner from "../components/LoadingSpinner";
import authService from "../services/authService";
import { useAuth } from "../hooks/useAuth";
import { ROUTES } from "../utils/constants";

export default function ProfilePage() {
  const navigate = useNavigate();
  const { user, setUser } = useAuth();
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    phone: "",
    address: "",
  });

  useEffect(() => {
    if (!user) {
      navigate(ROUTES.login);
      return;
    }

    setFormData({
      name: user.first_name || user.name || "",
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

    if (!formData.name || !formData.phone || !formData.address) {
      setError("All fields are required");
      return;
    }

    try {
      setLoading(true);
      const updateData = {
        first_name: formData.name,
        phone: formData.phone,
        address: formData.address,
      };
      const response = await authService.updateProfile(updateData);

      // Update auth context with new user data
      if (response.success && response.data && response.data.user && setUser) {
        setUser(response.data.user);
      } else if (response.data && setUser) {
        setUser(response.data);
      }

      setTimeout(() => window.location.reload(), 500);

      setSuccess("Profile updated successfully");
      setEditing(false);
      setError(null);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message || "Failed to update profile");
    } finally {
      setLoading(false);
    }
  };

  if (!user) return <LoadingSpinner />;

  return (
    <>
      <div className="container mx-auto px-4 py-8 max-w-md">
        <h1 className="text-3xl font-bold mb-8">My Profile</h1>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6">
            {success}
          </div>
        )}

        {!editing ? (
          // View Mode
          <div className="bg-white rounded-lg shadow p-6">
            <div className="mb-6">
              <label className="text-sm text-gray-600 font-semibold">
                Email
              </label>
              <p className="text-lg">{user.email}</p>
            </div>

            <div className="mb-6">
              <label className="text-sm text-gray-600 font-semibold">
                Role
              </label>
              <p className="text-lg capitalize">{user.role}</p>
            </div>

            <div className="mb-6">
              <label className="text-sm text-gray-600 font-semibold">
                Name
              </label>
              <p className="text-lg">{user.first_name || user.name || "N/A"}</p>
            </div>

            <div className="mb-6">
              <label className="text-sm text-gray-600 font-semibold">
                Phone
              </label>
              <p className="text-lg">{user.phone || "N/A"}</p>
            </div>

            <div className="mb-6">
              <label className="text-sm text-gray-600 font-semibold">
                Address
              </label>
              <p className="text-lg">{user.address || "N/A"}</p>
            </div>

            <div className="mb-6">
              <label className="text-sm text-gray-600 font-semibold">
                Member Since
              </label>
              <p className="text-lg">
                {new Date(user.created_at).toLocaleDateString()}
              </p>
            </div>

            <button
              onClick={() => setEditing(true)}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-semibold"
            >
              Edit Profile
            </button>
          </div>
        ) : (
          // Edit Mode
          <div className="bg-white rounded-lg shadow p-6">
            <form onSubmit={handleSaveProfile}>
              <div className="mb-6">
                <label className="block text-sm font-semibold mb-2">
                  Email (Read-Only)
                </label>
                <input
                  type="email"
                  value={user.email}
                  disabled
                  className="w-full px-4 py-2 border rounded bg-gray-100 cursor-not-allowed"
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-semibold mb-2">
                  Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleFormChange}
                  required
                  className="w-full px-4 py-2 border rounded"
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-semibold mb-2">
                  Phone *
                </label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleFormChange}
                  required
                  className="w-full px-4 py-2 border rounded"
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-semibold mb-2">
                  Address *
                </label>
                <textarea
                  name="address"
                  value={formData.address}
                  onChange={handleFormChange}
                  required
                  rows="3"
                  className="w-full px-4 py-2 border rounded"
                />
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setEditing(false);
                    setFormData({
                      name: user.first_name || user.name || "",
                      phone: user.phone || "",
                      address: user.address || "",
                    });
                  }}
                  className="flex-1 px-4 py-2 border rounded hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded font-semibold"
                >
                  {loading ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </>
  );
}
