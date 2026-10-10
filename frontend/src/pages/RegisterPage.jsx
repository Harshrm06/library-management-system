/**
 * Account registration page.
 *
 * The form is validated locally on every keystroke for fields the user has
 * already visited, so messages appear while typing without shouting at an
 * untouched form. Password strength is scored by `scorePasswordStrength`, which
 * reuses the same rules the API enforces, and the checklist under the field
 * shows exactly what is still missing.
 *
 * On success the API issues no token for a new member, so the user is redirected
 * to the login page with a confirmation. A duplicate email (HTTP 409) comes back
 * as a field error on the email input rather than a page-level banner.
 *
 * @example
 * // Submitted payload omits the client-only `confirmPassword` field.
 */

import { useMemo, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { CircularProgress, IconButton, InputAdornment } from "@mui/material";
import authService from "../services/authService";

import FormError from "../components/FormError";
import FormInput from "../components/FormInput";
import Toast from "../components/Toast";
import { useAuth } from "../hooks/useAuth";
import {
  scorePasswordStrength,
  validateRegistration,
} from "../utils/validators";
import { ROUTES } from "../utils/constants";

const EMPTY_FORM = {
  email: "",
  password: "",
  confirmPassword: "",
  first_name: "",
  last_name: "",
  phone: "",
  address: "",
};

/** Tailwind classes for each strength label. */
const STRENGTH_STYLES = {
  empty: {
    fill: "w-0",
    bar: "bg-ink-200",
    text: "text-ink-500",
    label: "Enter a password",
  },
  weak: {
    fill: "w-1/5",
    bar: "bg-red-500",
    text: "text-red-600",
    label: "Weak",
  },
  medium: {
    fill: "w-3/5",
    bar: "bg-amber-500",
    text: "text-amber-600",
    label: "Medium",
  },
  strong: {
    fill: "w-full",
    bar: "bg-emerald-500",
    text: "text-emerald-600",
    label: "Strong",
  },
};

/**
 * Render the registration form.
 *
 * @returns {JSX.Element} The page.
 */
export default function RegisterPage() {
  const {
    register,
    isAuthenticated,
    loading: sessionLoading,
    error: authError,
  } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  const busy = loading || sessionLoading;

  // Derived on every render: strength follows the password as it is typed.
  const { label: strengthLabel, requirements } = useMemo(
    () => scorePasswordStrength(formData.password),
    [formData.password],
  );
  const strength = STRENGTH_STYLES[strengthLabel];

  const validationErrors = useMemo(
    () => validateRegistration(formData),
    [formData],
  );
  const hasErrors = Object.keys(validationErrors).length > 0;

  if (!sessionLoading && isAuthenticated) {
    return <Navigate to={ROUTES.dashboard} replace />;
  }

  /**
   * Update one field and re-validate the fields already visited.
   *
   * @param {React.ChangeEvent<HTMLInputElement>} event The change event.
   */
  function handleChange(event) {
    const { name, value } = event.target;
    setFormData((current) => {
      const next = { ...current, [name]: value };
      if (Object.keys(touched).length > 0) {
        const fresh = validateRegistration(next);
        setErrors((currentErrors) => ({
          ...currentErrors,
          [name]: fresh[name],
        }));
      }
      return next;
    });
  }

  /**
   * Mark a field as visited so its message shows up.
   *
   * @param {string} name Field name.
   * @returns {void}
   */
  function handleBlur(name) {
    setTouched((current) => ({ ...current, [name]: true }));
    setErrors((current) => ({ ...current, [name]: validationErrors[name] }));
  }

  /**
   * Validate every field and create the account.
   *
   * @param {React.FormEvent<HTMLFormElement>} event The submit event.
   * @returns {Promise<void>} Resolves once the redirect is scheduled.
   */
  async function handleSubmit(event) {
    event.preventDefault();
    setErrors(validationErrors);
    if (hasErrors) return;

    setLoading(true);
    try {
      const result = await register(formData);

      if (result.success) {
        // Auto-login after registration
        setTimeout(async () => {
          try {
            const loginRes = await authService.login(
              formData.email,
              formData.password,
            );
            if (loginRes && loginRes.success) {
              navigate(ROUTES.dashboard, { replace: true });
            } else {
              navigate(ROUTES.login, { replace: true });
            }
          } catch (e) {
            navigate(ROUTES.login, { replace: true });
          }
        }, 1000);
        return;
      }

      setLoading(false);
      if (result.fieldErrors) {
        setErrors(result.fieldErrors);
      }
    } catch (err) {
      setLoading(false);
    }
  }

  return (
    <main className="page-container flex items-start justify-center py-10">
      <div className="mx-auto w-full max-w-lg">
        <div className="card p-6 sm:p-8">
          <header className="mb-6 text-center">
            <h1 className="text-2xl">Create your account</h1>
            <p className="mt-1 text-sm text-ink-600">
              Members can browse the catalog, borrow books and track loans.
            </p>
          </header>

          <Toast severity="error" message={authError} className="mb-4" />
          <button onClick={() => console.log("Button works!")}>
            Test Click
          </button>

          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormInput
                label="First name"
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
                onBlur={() => handleBlur("first_name")}
                error={errors.first_name}
                ariaLabel="First name"
                autoComplete="given-name"
                disabled={busy}
                required
              />
              <FormInput
                label="Last name"
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
                onBlur={() => handleBlur("last_name")}
                error={errors.last_name}
                ariaLabel="Last name"
                autoComplete="family-name"
                disabled={busy}
                required
              />
            </div>

            <FormInput
              label="Email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              onBlur={() => handleBlur("email")}
              error={errors.email}
              ariaLabel="Email address"
              autoComplete="email"
              disabled={busy}
              required
            />

            <div>
              <FormInput
                label="Password"
                name="password"
                type={showPassword ? "text" : "password"}
                value={formData.password}
                onChange={handleChange}
                onBlur={() => handleBlur("password")}
                error={errors.password}
                ariaLabel="Password"
                autoComplete="new-password"
                disabled={busy}
                required
                endAdornment={
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPassword((current) => !current)}
                      onMouseDown={(event) => event.preventDefault()}
                      edge="end"
                      size="small"
                      aria-label={
                        showPassword ? "Hide password" : "Show password"
                      }
                      aria-pressed={showPassword}
                    >
                      {showPassword ? "Hide" : "Show"}
                    </IconButton>
                  </InputAdornment>
                }
              />

              <div className="mt-2" aria-live="polite">
                <div className="flex items-center gap-2">
                  <div
                    className="h-1.5 flex-1 overflow-hidden rounded-full bg-ink-200"
                    role="progressbar"
                    aria-label="Password strength"
                    aria-valuemin={0}
                    aria-valuemax={5}
                    aria-valuenow={
                      requirements.filter((item) => item.met).length
                    }
                    aria-valuetext={strength.label}
                  >
                    <div
                      className={`h-full rounded-full transition-all ${strength.bar} ${strength.fill}`}
                    />
                  </div>
                  <span className={`text-xs font-medium ${strength.text}`}>
                    {strength.label}
                  </span>
                </div>

                <ul className="mt-2 grid grid-cols-1 gap-1 text-xs sm:grid-cols-2">
                  {requirements.map((requirement) => (
                    <li
                      key={requirement.id}
                      className={
                        requirement.met ? "text-emerald-600" : "text-ink-500"
                      }
                    >
                      <span aria-hidden="true">
                        {requirement.met ? "✓" : "•"}
                      </span>{" "}
                      {requirement.label}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <FormInput
              label="Confirm password"
              name="confirmPassword"
              type={showPassword ? "text" : "password"}
              value={formData.confirmPassword}
              onChange={handleChange}
              onBlur={() => handleBlur("confirmPassword")}
              error={errors.confirmPassword}
              ariaLabel="Confirm password"
              autoComplete="new-password"
              disabled={busy}
              required
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <FormInput
                label="Phone (optional)"
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                error={errors.phone}
                ariaLabel="Phone number, optional"
                autoComplete="tel"
                disabled={busy}
              />
              <FormInput
                label="Address (optional)"
                name="address"
                value={formData.address}
                onChange={handleChange}
                error={errors.address}
                ariaLabel="Postal address, optional"
                autoComplete="street-address"
                disabled={busy}
              />
            </div>

            <label className="flex items-start gap-2 text-sm text-ink-700">
              <input
                type="checkbox"
                name="acceptedTerms"
                checked={acceptedTerms}
                onChange={(event) => setAcceptedTerms(event.target.checked)}
                disabled={busy}
                className="mt-0.5 h-4 w-4 rounded border-ink-300 text-brand-600 focus:ring-brand-500"
                aria-label="Accept the terms of service"
              />
              <span>
                I accept the library terms of service. (Optional in this
                preview.)
              </span>
            </label>

            <button
              type="submit"
              className="btn-primary w-full"
              disabled={busy || hasErrors}
            >
              {busy ? (
                <span className="flex items-center justify-center gap-2">
                  <CircularProgress
                    size={18}
                    color="inherit"
                    aria-hidden="true"
                  />
                  {loading ? "Creating account…" : "Restoring session…"}
                </span>
              ) : (
                "Create account"
              )}
            </button>

            <FormError
              message={hasErrors ? "Please fix the highlighted fields." : ""}
              className="text-center"
            />
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-ink-600">
          Already have an account?{" "}
          <Link
            to={ROUTES.login}
            className="font-medium text-brand-700 hover:text-brand-800"
          >
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
