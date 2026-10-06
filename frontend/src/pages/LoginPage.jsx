/**
 * Sign-in page.
 *
 * Validates locally before contacting the API, keeps the submit button disabled
 * while the form is invalid, and sends the user to the dashboard once
 * `useAuth().login()` reports success. Errors raised by the API (wrong password,
 * deactivated account, server down) arrive as a message on the auth context and
 * are rendered with `Toast`.
 *
 * "Remember me" is not cosmetic: `login(..., { remember })` decides whether the
 * token is kept in `localStorage` (survives a browser restart) or in
 * `sessionStorage` (dropped when the tab closes).
 *
 * @example
 * // Visiting /login while signed in redirects straight to the dashboard.
 */

import { useEffect, useMemo, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { CircularProgress, IconButton, InputAdornment } from '@mui/material';

import FormError from '../components/FormError';
import FormInput from '../components/FormInput';
import Toast from '../components/Toast';
import { useAuth } from '../hooks/useAuth';
import { validateLogin } from '../utils/validators';
import { ROUTES, STORAGE_KEYS } from '../utils/constants';

const EMPTY_FORM = { email: '', password: '' };

/** Placeholder copy for the password reset link, which the API does not expose. */
const FORGOT_PASSWORD_MESSAGE =
  'Password reset is not available yet. Please contact the library desk.';

/**
 * Read the stored "remember me" preference.
 *
 * @returns {boolean} True when the checkbox should start ticked.
 */
function readRememberMe() {
  try {
    return window.localStorage.getItem(STORAGE_KEYS.rememberMe) === 'true';
  } catch {
    return true;
  }
}

/**
 * Render the sign-in form.
 *
 * @returns {JSX.Element} The page.
 */
export default function LoginPage() {
  const { login, isAuthenticated, loading: sessionLoading, error: authError } = useAuth();
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

  // Field errors are derived from the current values, so a corrected field
  // clears its message as soon as the user types.
  const fieldErrors = useMemo(() => validateLogin(values), [values]);
  const hasErrors = Object.keys(fieldErrors).length > 0;

  // A one-off banner from a previous page is cleared on arrival.
  useEffect(() => {
    if (registered || sessionExpired) {
      setErrors({});
    }
  }, [registered, sessionExpired]);

  if (!sessionLoading && isAuthenticated) {
    return <Navigate to={ROUTES.dashboard} replace />;
  }

  /**
   * Update one field and drop its error.
   *
   * @param {React.ChangeEvent<HTMLInputElement>} event The change event.
   */
  function handleChange(event) {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
  }

  /**
   * Validate a single field once it has been left.
   *
   * @param {string} name Field name.
   * @returns {void}
   */
  function handleBlur(name) {
    const message = fieldErrors[name];
    setErrors((current) => ({ ...current, [name]: message }));
  }

  /**
   * Validate and submit the credentials.
   *
   * @param {React.FormEvent<HTMLFormElement>} event The submit event.
   * @returns {Promise<void>} Resolves once the navigation is scheduled.
   */
  async function handleSubmit(event) {
    event.preventDefault();
    setErrors(fieldErrors);
    if (hasErrors) return;

    setLoading(true);
    try {
      const result = await login(values.email, values.password, { remember: rememberMe });
      if (result.success) {
        navigate(location.state?.from?.pathname ?? ROUTES.dashboard, { replace: true });
      } else {
        setLoading(false);
      }
    } catch {
      // The service reports failures as data, so this only guards a broken
      // provider: never leave the button spinning forever.
      setLoading(false);
    }
  }

  return (
    <main className="page-container flex items-start justify-center py-10">
      <div className="mx-auto w-full max-w-md">
        <div className="card p-6 sm:p-8">
          <header className="mb-6 text-center">
            <h1 className="text-2xl">Sign in</h1>
            <p className="mt-1 text-sm text-ink-600">
              Use your library account to browse the catalog and borrow books.
            </p>
          </header>

          {registered ? (
            <Toast
              severity="success"
              message="Account created. Sign in to continue."
              className="mb-4"
              onClose={() => navigate(ROUTES.login, { replace: true, state: {} })}
            />
          ) : null}

          {sessionExpired ? (
            <Toast
              severity="warning"
              message="Your session expired. Please sign in again."
              className="mb-4"
              onClose={() => navigate(ROUTES.login, { replace: true, state: {} })}
            />
          ) : null}

          <Toast severity="error" message={authError} className="mb-4" />
          <Toast
            severity="info"
            message={notice}
            className="mb-4"
            onClose={() => setNotice('')}
          />

          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            <FormInput
              label="Email"
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

            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-sm text-ink-700">
                <input
                  type="checkbox"
                  name="rememberMe"
                  checked={rememberMe}
                  onChange={(event) => setRememberMe(event.target.checked)}
                  disabled={busy}
                  className="h-4 w-4 rounded border-ink-300 text-brand-600 focus:ring-brand-500"
                  aria-label="Remember me on this device"
                />
                Remember me
              </label>

              <button
                type="button"
                onClick={() => setNotice(FORGOT_PASSWORD_MESSAGE)}
                className="text-sm font-medium text-brand-700 underline underline-offset-2 hover:text-brand-800"
              >
                Forgot password?
              </button>
            </div>

            <button type="submit" className="btn-primary w-full" disabled={busy || hasErrors}>
              {busy ? (
                <span className="flex items-center justify-center gap-2">
                  <CircularProgress size={18} color="inherit" aria-hidden="true" />
                  {loading ? 'Signing in…' : 'Restoring session…'}
                </span>
              ) : (
                'Sign in'
              )}
            </button>

            <FormError
              message={hasErrors ? 'Please fix the highlighted fields.' : ''}
              className="text-center"
            />
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-ink-600">
          Need an account?{' '}
          <Link to={ROUTES.register} className="font-medium text-brand-700 hover:text-brand-800">
            Sign up
          </Link>
        </p>
      </div>
    </main>
  );
}
