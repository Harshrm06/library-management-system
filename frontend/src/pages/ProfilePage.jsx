/**
 * Profile page: view the current account and edit its editable fields.
 *
 * Reads through `getCurrentUser()` so the screen always reflects the server, and
 * saves through `updateProfile()`, which sends only the fields that changed. Role
 * and email are shown but not editable - the API does not accept them.
 *
 * @example
 * // Arriving from "Edit profile" focuses the form.
 * <ProfilePage />   // location.state = { edit: true }
 */

import { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { CircularProgress } from '@mui/material';

import FormError from '../components/FormError';
import FormInput from '../components/FormInput';
import LoadingSpinner from '../components/LoadingSpinner';
import Toast from '../components/Toast';
import { useAuth } from '../hooks/useAuth';
import { getCurrentUser, updateProfile } from '../services/authService';
import { formatDate } from '../utils/helpers';

/** Fields the user may change. */
const EDITABLE_FIELDS = ['first_name', 'last_name', 'phone', 'address'];

/**
 * Turn a profile into the editable form state.
 *
 * @param {object} profile The user from the API.
 * @returns {{ first_name: string, last_name: string, phone: string, address: string }} Form values.
 */
function toFormValues(profile) {
  return {
    first_name: profile?.first_name ?? '',
    last_name: profile?.last_name ?? '',
    phone: profile?.phone ?? '',
    address: profile?.address ?? '',
  };
}

/**
 * Render the profile screen.
 *
 * @returns {JSX.Element} The page.
 */
export default function ProfilePage() {
  // Aliased to avoid colliding with the local `setError` below, which renders the
  // message on this page; the context one raises the shared header toast.
  const { setError: setAuthError } = useAuth();
  const location = useLocation();
  const startedEditing = Boolean(location.state?.edit);

  const [profile, setProfile] = useState(null);
  const [values, setValues] = useState(null);
  const [editing, setEditing] = useState(startedEditing);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    const result = await getCurrentUser();
    setLoading(false);
    if (!result.success) {
      setError(result.message);
      setAuthError(result.message);
      return;
    }
    setProfile(result.data.user);
    setValues(toFormValues(result.data.user));
  }, [setAuthError]);

  useEffect(() => {
    load();
  }, [load]);

  /**
   * Update one editable field.
   *
   * @param {React.ChangeEvent<HTMLInputElement>} event The change event.
   */
  function handleChange(event) {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
  }

  /**
   * Send the changed fields to the API.
   *
   * @param {React.FormEvent<HTMLFormElement>} event The submit event.
   * @returns {Promise<void>} Resolves once the save settles.
   */
  async function handleSubmit(event) {
    event.preventDefault();
    if (!profile) return;

    const changes = {};
    for (const field of EDITABLE_FIELDS) {
      if (values[field] !== (profile[field] ?? '')) changes[field] = values[field];
    }
    if (Object.keys(changes).length === 0) {
      setEditing(false);
      return;
    }

    setSaving(true);
    setError('');
    const result = await updateProfile(changes);
    setSaving(false);
    if (!result.success) {
      setError(result.message);
      setAuthError(result.message);
      return;
    }
    setProfile(result.data.user);
    setValues(toFormValues(result.data.user));
    setEditing(false);
  }

  if (loading || !values) {
    return <LoadingSpinner label="Loading your profile…" />;
  }

  return (
    <main className="page-container">
      <header className="mb-6">
        <h1 className="text-2xl">My profile</h1>
        <p className="mt-1 text-sm text-ink-600">
          Your name and contact details, as the library has them on record.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="card lg:col-span-1">
          <h2 className="text-sm font-medium uppercase tracking-wide text-ink-500">Account</h2>
          <dl className="mt-3 space-y-3 text-sm">
            <div>
              <dt className="text-ink-500">Email</dt>
              <dd className="font-medium text-ink-900">{profile?.email}</dd>
            </div>
            <div>
              <dt className="text-ink-500">Role</dt>
              <dd className="font-medium capitalize text-ink-900">{profile?.role}</dd>
            </div>
            <div>
              <dt className="text-ink-500">Member since</dt>
              <dd className="font-medium text-ink-900">{formatDate(profile?.created_at)}</dd>
            </div>
            <div>
              <dt className="text-ink-500">Status</dt>
              <dd className="font-medium text-ink-900">
                {profile?.is_active ? 'Active' : 'Inactive'}
              </dd>
            </div>
          </dl>
        </section>

        <section className="card lg:col-span-2">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg">Personal details</h2>
            {editing ? null : (
              <button type="button" className="btn-secondary" onClick={() => setEditing(true)}>
                Edit
              </button>
            )}
          </div>

          <Toast severity="error" message={error} className="mb-4" />

          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormInput
                label="First name"
                name="first_name"
                value={values.first_name}
                onChange={handleChange}
                ariaLabel="First name"
                autoComplete="given-name"
                disabled={!editing || saving}
              />
              <FormInput
                label="Last name"
                name="last_name"
                value={values.last_name}
                onChange={handleChange}
                ariaLabel="Last name"
                autoComplete="family-name"
                disabled={!editing || saving}
              />
            </div>

            <FormInput
              label="Phone"
              name="phone"
              type="tel"
              value={values.phone}
              onChange={handleChange}
              ariaLabel="Phone number"
              autoComplete="tel"
              disabled={!editing || saving}
            />
            <FormInput
              label="Address"
              name="address"
              value={values.address}
              onChange={handleChange}
              ariaLabel="Postal address"
              autoComplete="street-address"
              disabled={!editing || saving}
            />

            {editing ? (
              <div className="flex flex-wrap gap-3">
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? (
                    <span className="flex items-center gap-2">
                      <CircularProgress size={16} color="inherit" aria-hidden="true" />
                      Saving…
                    </span>
                  ) : (
                    'Save changes'
                  )}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setValues(toFormValues(profile));
                    setEditing(false);
                  }}
                  disabled={saving}
                >
                  Cancel
                </button>
              </div>
            ) : (
              <FormError message="" />
            )}
          </form>
        </section>
      </div>
    </main>
  );
}
