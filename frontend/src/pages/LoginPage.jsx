/**
 * Sign-in page.
 *
 * Validates locally before contacting the API, manages "remember me",
 * and sends the user to their dashboard once authenticated.
 * Displays clean library aesthetic.
 */

import { useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { CircularProgress, IconButton, InputAdornment } from '@mui/material';

import FormError from '../components/FormError';
import FormInput from '../components/FormInput';
import Toast from '../components/Toast';
import { useAuth } from '../hooks/useAuth';
import { validateLogin } from '../utils/validators';
import { ROUTES, STORAGE_KEYS } from '../utils/constants';

const EMPTY_FORM = { email: '', password: '' };

const FORGOT_PASSWORD_MESSAGE =
  'Password reset is managed by library staff. Please contact the library administrator desk.';

function readRememberMe() {
  try {
    return window.localStorage.getItem(STORAGE_KEYS.rememberMe) === 'true';
  } catch {
    return true;
  }
}

export default function LoginPage() {
  const { login, isAuthenticated, isAdmin, loading: sessionLoading, error: authError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [values, setValues] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(readRememberMe);
  const [notice, setNotice] = useState('');

  const registered = Boolean(location.state?.registered);
  const sessionExpired = Boolean(location.state?.sessionExpired);
  const busy = loading || sessionLoading;

  const fieldErrors = useMemo(() => validateLogin(values), [values]);
  const hasErrors = Object.keys(fieldErrors).length > 0;

  useEffect(() => {
    if (registered || sessionExpired) {
      setErrors({});
    }
  }, [registered, sessionExpired]);

  if (!sessionLoading && isAuthenticated) {
    return <Navigate to={isAdmin ? ROUTES.adminDashboard : ROUTES.dashboard} replace />;
  }

  function handleChange(event) {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
  }

  function handleBlur(name) {
    const message = fieldErrors[name];
    setErrors((current) => ({ ...current, [name]: message }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setErrors(fieldErrors);
    if (hasErrors) return;

    setLoading(true);
    try {
      const result = await login(values.email, values.password, { remember: rememberMe });
      if (result.success) {
        const dest = location.state?.from?.pathname ?? (result.data?.user?.role === 'admin' ? ROUTES.adminDashboard : ROUTES.dashboard);
        navigate(dest, { replace: true });
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  }

  return (
    <main className="page-container flex min-h-[80vh] items-center justify-center py-12">
      <div className="mx-auto w-full max-w-md">
        {/* Library Branding Icon */}
        <div className="mb-6 text-center">
          <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-700 text-white shadow-elevation ring-1 ring-brand-800">
            <svg
              className="h-7 w-7"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
              <path d="M6 6h10" />
              <path d="M6 10h10" />
              <path d="M6 14h6" />
            </svg>
          </div>
          <h2 className="mt-3 font-serif text-2xl font-bold tracking-tight text-brand-950 sm:text-3xl">
            Athenaeum Library
          </h2>
          <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-forest-700">
            Digital Management System
          </p>
        </div>

        <div className="card border-cream-300 bg-white p-6 sm:p-8 shadow-elevation rounded-2xl">
          <header className="mb-6">
            <h1 className="font-serif text-xl font-bold text-ink-900">Sign in to your account</h1>
            <p className="mt-1 text-xs text-ink-500">
              Enter your library card credentials to access circulation and catalog holdings.
            </p>
          </header>

          {registered && (
            <Toast
              severity="success"
              message="Account registered. Sign in with your credentials."
              className="mb-4"
              onClose={() => navigate(ROUTES.login, { replace: true, state: {} })}
            />
          )}

          {sessionExpired && (
            <Toast
              severity="warning"
              message="Your session has expired. Please sign in again."
              className="mb-4"
              onClose={() => navigate(ROUTES.login, { replace: true, state: {} })}
            />
          )}

          <Toast severity="error" message={authError} className="mb-4" />
          <Toast
            severity="info"
            message={notice}
            className="mb-4"
            onClose={() => setNotice('')}
          />

          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            <FormInput
              label="Email Address"
              name="email"
              type="email"
              value={values.email}
              onChange={handleChange}
              onBlur={() => handleBlur('email')}
              error={errors.email}
              ariaLabel="Email address"
              autoComplete="email"
              autoFocus
              disabled={busy}
              required
            />

            <FormInput
              label="Password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              value={values.password}
              onChange={handleChange}
              onBlur={() => handleBlur('password')}
              error={errors.password}
              ariaLabel="Password"
              autoComplete="current-password"
              disabled={busy}
              required
              endAdornment={
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowPassword((current) => !current)}
                    onMouseDown={(event) => event.preventDefault()}
                    edge="end"
                    size="small"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    aria-pressed={showPassword}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </IconButton>
                </InputAdornment>
              }
            />

            <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
              <label className="flex items-center gap-2 text-xs text-ink-700 cursor-pointer">
                <input
                  type="checkbox"
                  name="rememberMe"
                  checked={rememberMe}
                  onChange={(event) => setRememberMe(event.target.checked)}
                  disabled={busy}
                  className="h-4 w-4 rounded border-cream-300 text-brand-600 focus:ring-brand-500"
                  aria-label="Remember me on this device"
                />
                <span>Remember me</span>
              </label>

              <button
                type="button"
                onClick={() => setNotice(FORGOT_PASSWORD_MESSAGE)}
                className="text-xs font-semibold text-brand-700 hover:text-brand-900 underline-offset-2 hover:underline"
              >
                Forgot password?
              </button>
            </div>

            <button
              type="submit"
              className="btn-primary w-full py-2.5 mt-2 text-sm font-semibold shadow-md"
              disabled={busy || hasErrors}
            >
              {busy ? (
                <span className="flex items-center justify-center gap-2">
                  <CircularProgress size={18} color="inherit" aria-hidden="true" />
                  {loading ? 'Authenticating…' : 'Restoring…'}
                </span>
              ) : (
                'Sign In'
              )}
            </button>

            <FormError
              message={hasErrors ? 'Please verify all required credentials.' : ''}
              className="text-center"
            />
          </form>
        </div>

        {/* Phase 5 Notice: Member accounts created by admin */}
        <div className="mt-6 text-center text-xs text-ink-500 bg-cream-50/80 p-3.5 rounded-xl border border-cream-200">
          <p className="font-medium text-ink-700">Need a Library Card?</p>
          <p className="mt-0.5">
            Member accounts are registered by library staff. Please contact your library administrator.
          </p>
        </div>
      </div>
    </main>
  );
}
