/**
 * Authentication service.
 *
 * Thin, typed wrappers around the auth endpoints in
 * `backend/app/routes/auth_routes.py`. Every function follows the same rules:
 *
 * * it never throws - transport, timeout and HTTP failures are converted into a
 *   structured {@link ServiceResult} so callers can branch without try/catch,
 * * it returns `{ success, data, error, message }`, where `message` is always
 *   safe to display and `error` carries the status, code and per-field messages,
 * * it maps the camelCase form state used by the pages onto the snake_case body
 *   the API expects.
 *
 * The response body from the API is `{ success, message, data, timestamp }`;
 * `data` below is the small, named object documented per function.
 *
 * @example
 * const result = await login('member@example.com', 'secretpass1');
 * if (result.success) {
 *   navigate(ROUTES.catalog);
 * } else {
 *   showError(result.message);
 * }
 *
 * @example
 * // Errors are data, not exceptions:
 * const profile = await updateProfile({ phone: '+1-555-0199' });
 * if (!profile.success) console.warn(profile.error.status, profile.error.code);
 */

import api, { clearStoredSession, handleApiError } from './api';
import { AUTH_ENDPOINTS } from '../utils/constants';

/**
 * @typedef {import('./api').ServiceResult} ServiceResult
 * @typedef {import('./api').ApiError} ApiError
 */

/**
 * Read the payload out of a success envelope.
 *
 * @param {import('axios').AxiosResponse} response The axios response.
 * @returns {object|null} The `data` member of the envelope, or null.
 */
function envelopeData(response) {
  const body = response?.data;
  return body && typeof body === 'object' && 'data' in body ? body.data : null;
}

/**
 * Read the message out of a success envelope.
 *
 * @param {import('axios').AxiosResponse} response The axios response.
 * @param {string} fallback Message to use when the body carries none.
 * @returns {string} The server message, or `fallback`.
 */
function envelopeMessage(response, fallback) {
  const message = response?.data?.message;
  return typeof message === 'string' && message ? message : fallback;
}

/**
 * Build the successful result shape.
 *
 * @param {object|null} data Named payload documented by the caller function.
 * @param {string} message Human readable outcome.
 * @returns {ServiceResult} `{ success: true, data, error: null, message }`.
 */
function ok(data, message) {
  return { success: true, data, error: null, message };
}

/**
 * Build the failed result shape from an axios error.
 *
 * @param {unknown} error The rejected value from an axios call.
 * @param {string} fallback Message to use when the failure carries none.
 * @returns {ServiceResult} `{ success: false, data: null, error, message }`.
 */
function fail(error, fallback) {
  const normalized = handleApiError(error);
  return {
    success: false,
    data: null,
    error: normalized,
    message: normalized.message || fallback,
  };
}

/**
 * Read a field that may be spelled in camelCase or snake_case.
 *
 * Page state uses camelCase (`firstName`) while the API uses snake_case
 * (`first_name`); accepting both keeps the forms free of translation code.
 *
 * @param {Record<string, unknown>} source Object to read from.
 * @param {string} camelKey camelCase key.
 * @param {string} snakeKey snake_case key.
 * @returns {unknown} The first key that is present, otherwise undefined.
 */
function pick(source, camelKey, snakeKey) {
  if (!source || typeof source !== 'object') return undefined;
  if (source[camelKey] !== undefined) return source[camelKey];
  return source[snakeKey];
}

/**
 * Exchange credentials for an access token.
 *
 * A wrong password answers 401; the request is flagged `skipAuthHandling` so the
 * response interceptor neither clears an existing session nor redirects away
 * from the login form.
 *
 * @param {string} email Registered email address.
 * @param {string} password Account password.
 * @returns {Promise<ServiceResult>} On success `data` is
 *   `{ token, token_type, expires_in, user }`; on failure `error.status` is 401
 *   with code `invalid_credentials`.
 *
 * @example
 * const { success, data, error } = await login(email, password);
 * if (!success && error.code === 'invalid_credentials') setFormError(error.message);
 */
export async function login(email, password) {
  try {
    const response = await api.post(
      AUTH_ENDPOINTS.login,
      { email, password },
      { meta: { skipAuthHandling: true, skipAuthRedirect: true } },
    );
    const payload = envelopeData(response) || {};
    return ok(
      {
        token: payload.token,
        token_type: payload.token_type,
        expires_in: payload.expires_in,
        user: payload.user,
      },
      envelopeMessage(response, 'Login successful'),
    );
  } catch (error) {
    return fail(error, 'Unable to sign in. Please try again.');
  }
}

/**
 * Create a new member account.
 *
 * The API returns no token for a new member, so the caller sends the user to
 * the login page after a successful call.
 *
 * @param {{ email: string, password: string, firstName?: string, first_name?: string, lastName?: string, last_name?: string, phone?: string, address?: string }} formData
 *   Registration values; first and last name may be given in either case style.
 * @returns {Promise<ServiceResult>} On success `data` is `{ user }`. A duplicate
 *   email fails with status 409 and code `email_taken`; invalid input fails with
 *   status 422 and `error.fieldErrors` keyed by field name.
 *
 * @example
 * const result = await register(values);
 * if (!result.success && result.error.fieldErrors.email) {
 *   setErrors(result.error.fieldErrors);
 * }
 */
export async function register(formData) {
  const payload = {
    email: formData?.email,
    password: formData?.password,
    first_name: pick(formData, 'firstName', 'first_name'),
    last_name: pick(formData, 'lastName', 'last_name'),
  };
  if (formData?.phone !== undefined && formData?.phone !== '') payload.phone = formData.phone;
  if (formData?.address !== undefined && formData?.address !== '') payload.address = formData.address;

  try {
    const response = await api.post(AUTH_ENDPOINTS.register, payload, {
      meta: { skipAuthHandling: true, skipAuthRedirect: true },
    });
    const data = envelopeData(response) || {};
    return ok({ user: data.user }, envelopeMessage(response, 'Account created successfully'));
  } catch (error) {
    return fail(error, 'Unable to create the account. Please try again.');
  }
}

/**
 * Mint a new access token for the current session.
 *
 * The API is stateless, so refreshing re-checks the account. An expired token
 * answers 401: the interceptor clears the stored session, and this call reports
 * it without redirecting.
 *
 * @returns {Promise<ServiceResult>} On success `data` is `{ token }`.
 *
 * @example
 * const { success, data } = await refreshToken();
 * if (success) setAuthToken(data.token);
 */
export async function refreshToken() {
  try {
    const response = await api.post(
      AUTH_ENDPOINTS.refreshToken,
      null,
      { meta: { skipAuthRedirect: true } },
    );
    const body = response?.data || {};
    return ok({ token: body.token }, envelopeMessage(response, 'Token refreshed'));
  } catch (error) {
    return fail(error, 'Your session could not be refreshed. Please sign in again.');
  }
}

/**
 * Acknowledge a logout and drop the stored session.
 *
 * Tokens are not revoked server-side, so the local copy is discarded even when
 * the call fails; only a confirmed call clears storage here, and the caller
 * always clears its own React state.
 *
 * @returns {Promise<ServiceResult>} On success `data` is `{ success: true }` and
 *   the token has been removed from `localStorage`.
 *
 * @example
 * await logout();
 * navigate(ROUTES.login, { replace: true });
 */
export async function logout() {
  try {
    const response = await api.post(
      AUTH_ENDPOINTS.logout,
      null,
      { meta: { skipAuthRedirect: true } },
    );
    clearStoredSession();
    return ok({ success: true }, envelopeMessage(response, 'Logged out'));
  } catch (error) {
    return fail(error, 'Signed out locally; the server could not be reached.');
  }
}

/**
 * Fetch the authenticated profile.
 *
 * Answers 401 when the token is missing, expired or invalid, and 404 when the
 * account behind a valid token no longer exists; both mean "not authenticated"
 * and are reported through `error.status`.
 *
 * @returns {Promise<ServiceResult>} On success `data` is `{ user }`.
 *
 * @example
 * const { success, data } = await getCurrentUser();
 * if (!success) clearSession();
 */
export async function getCurrentUser() {
  try {
    const response = await api.get(AUTH_ENDPOINTS.me);
    return ok({ user: response?.data }, 'Profile loaded');
  } catch (error) {
    return fail(error, 'Your profile could not be loaded.');
  }
}

/**
 * Apply a partial update to the authenticated profile.
 *
 * Only the four editable fields are copied into the request body, so unknown
 * keys (`role`, in particular) are dropped instead of being sent and rejected.
 * `role` is not accepted by the API.
 *
 * @param {{ firstName?: string, first_name?: string, lastName?: string, last_name?: string, phone?: string, address?: string }} profileData
 *   Fields to change; name fields may be given in either case style.
 * @returns {Promise<ServiceResult>} On success `data` is `{ user }` with the
 *   updated profile.
 *
 * @example
 * const { success, data, error } = await updateProfile({ phone: '+1-555-0199' });
 * if (success) setProfile(data.user);
 * else setErrors(error.fieldErrors);
 */
export async function updateProfile(profileData) {
  const payload = {};
  const firstName = pick(profileData, 'firstName', 'first_name');
  const lastName = pick(profileData, 'lastName', 'last_name');
  if (firstName !== undefined) payload.first_name = firstName;
  if (lastName !== undefined) payload.last_name = lastName;
  if (profileData?.phone !== undefined) payload.phone = profileData.phone;
  if (profileData?.address !== undefined) payload.address = profileData.address;

  try {
    const response = await api.put(AUTH_ENDPOINTS.me, payload);
    return ok({ user: response?.data }, envelopeMessage(response, 'Profile updated'));
  } catch (error) {
    return fail(error, 'Your profile could not be updated.');
  }
}

export default {
  login,
  register,
  refreshToken,
  logout,
  getCurrentUser,
  updateProfile,
};