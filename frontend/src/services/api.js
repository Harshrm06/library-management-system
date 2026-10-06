/**
 * Shared HTTP client for the Library Management System.
 *
 * Creates one axios instance that every service uses, so authentication,
 * error reporting and timeouts are implemented exactly once:
 *
 * 1. **Request interceptor** - reads the JWT from `localStorage` and attaches
 *    it as `Authorization: Bearer {token}` when a token exists. Requests without
 *    a token are sent untouched (public endpoints such as login).
 * 2. **Response interceptor** - translates HTTP failures into one predictable
 *    shape: 401 clears the session and sends the user to the login page, 403 /
 *    404 / 500 raise a human readable message, and every error is enriched with
 *    `status`, `code`, `details` and `fieldErrors` before it is re-thrown.
 *
 * The backend answers with the envelope `{ success, message, data, timestamp }`,
 * which is passed through untouched: `response.data` is always the server body,
 * never a partially unwrapped guess. Services unwrap it explicitly.
 *
 * The UI layer is never imported here. Instead the application registers a
 * handler with {@link registerApiEventHandler} and decides what to render, which
 * keeps this module testable outside React.
 *
 * @example
 * import api, { API_BASE_URL, handleApiError } from '../services/api';
 *
 * try {
 *   const response = await api.get('/api/auth/me');
 *   console.log(response.data.data);
 * } catch (error) {
 *   console.error(handleApiError(error).message, error.status);
 * }
 */

import axios from 'axios';

import { API_BASE_URL, ROUTES, STORAGE_KEYS } from '../utils/constants';

/** Request timeout in milliseconds. */
export const REQUEST_TIMEOUT_MS = 10000;

/**
 * @typedef {Object} ApiError
 * @property {number|null} status HTTP status code, or null for network failures.
 * @property {string} code Machine readable code, e.g. `email_taken` or `timeout`.
 * @property {string} message User friendly message, safe to display.
 * @property {string} details Server supplied explanation, when present.
 * @property {string[]} issues Raw validation messages (HTTP 422).
 * @property {Record<string, string>} fieldErrors Field name -> message, for forms.
 */

/**
 * @typedef {Object} ServiceResult
 * @property {boolean} success True when the call succeeded.
 * @property {object|null} data Payload from the response envelope, or null.
 * @property {ApiError|null} error Normalized failure details, or null on success.
 * @property {string} message Human readable outcome, always populated.
 */

/**
 * @typedef {Object} ApiEvent
 * @property {number|null} status HTTP status code, or null for network failures.
 * @property {string} code Machine readable error code.
 * @property {string} message User friendly message.
 * @property {boolean} isUnauthorized True for 401 responses.
 */

/**
 * @typedef {Object} ApiEventHandler
 * @property {(event: ApiEvent) => void} [onUnauthorized] Called after a 401
 *   cleared the stored session, so the app can navigate to the login page.
 * @property {(event: ApiEvent) => void} [onError] Called for 403 / 404 / 500 so
 *   the app can show the message.
 */

/** Default English copy for every status the API can return. */
export const ERROR_MESSAGES = {
  400: 'That request could not be processed. Please check the values and try again.',
  401: 'Your session has expired. Please sign in again.',
  403: 'You do not have permission to perform this action.',
  404: 'The requested resource was not found.',
  409: 'That record already exists.',
  422: 'Some of the details provided are not valid.',
  429: 'Too many requests. Please wait a moment and try again.',
  500: 'The server ran into a problem. Please try again.',
  502: 'The server is temporarily unavailable. Please try again shortly.',
  503: 'The server is temporarily unavailable. Please try again shortly.',
  504: 'The server took too long to respond. Please try again.',
};

/** Message used when the failure carries no status at all. */
export const NETWORK_ERROR_MESSAGE =
  'Could not reach the server. Please check your connection and try again.';

/** Message used when the request exceeded {@link REQUEST_TIMEOUT_MS}. */
export const TIMEOUT_ERROR_MESSAGE =
  'The request took too long to complete. Please try again.';

/** Statuses whose message the response interceptor forwards to the UI. */
const REPORTED_STATUSES = [403, 404, 500];

/** @type {string|null} In-memory token, so hot paths skip localStorage reads. */
let authToken = null;

/** @type {ApiEventHandler|null} Handler registered by the application shell. */
let eventHandler = null;

/**
 * Read one key from a storage area that may be unavailable.
 *
 * Browsers throw a `SecurityError` when storage is blocked (private mode, some
 * embedded webviews). Each area is read separately so a broken `sessionStorage`
 * cannot also take `localStorage` down with it.
 *
 * @param {Storage|undefined} storage Storage area to read.
 * @param {string} key Key to read.
 * @returns {string|null} The value, or null when absent or blocked.
 */
function safeGet(storage, key) {
  try {
    return storage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

/**
 * Write one key to a storage area that may be unavailable.
 *
 * @param {Storage|undefined} storage Storage area to write.
 * @param {string} key Key to write.
 * @param {string|null} value Value to store, or null to remove the key.
 * @returns {boolean} True when the write happened.
 */
function safeSet(storage, key, value) {
  try {
    if (!storage) return false;
    if (value === null) {
      storage.removeItem(key);
    } else {
      storage.setItem(key, value);
    }
    return true;
  } catch {
    return false;
  }
}

/**
 * Register the callback that turns HTTP failures into UI behaviour.
 *
 * The handler is invoked *after* the session has been cleared, so it only has
 * to decide where to navigate or what to show.
 *
 * @param {ApiEventHandler|null} handler Handler object, or null to remove it.
 * @returns {void}
 *
 * @example
 * registerApiEventHandler({
 *   onUnauthorized: () => navigate(ROUTES.login, { replace: true }),
 *   onError: ({ message }) => showToast(message),
 * });
 */
export function registerApiEventHandler(handler) {
  eventHandler = handler;
}

/**
 * Read the persisted access token.
 *
 * "Remember me" decides where the token lives: `localStorage` survives a browser
 * restart, `sessionStorage` does not. Both are checked, in that order.
 *
 * @returns {string|null} The stored JWT, or null when signed out or when
 *   storage is unavailable (private browsing).
 */
export function getStoredToken() {
  if (authToken) return authToken;
  authToken =
    safeGet(window.localStorage, STORAGE_KEYS.token) ??
    safeGet(window.sessionStorage, STORAGE_KEYS.token);
  return authToken;
}

/**
 * Persist (or clear) the token used by the request interceptor.
 *
 * @param {string|null} token JWT to store, or null to sign out.
 * @param {{ persist?: boolean }} [options] `persist: false` keeps the token in
 *   `sessionStorage` so it disappears when the tab closes.
 * @returns {void}
 */
export function setAuthToken(token, { persist = true } = {}) {
  authToken = token;
  const target = persist ? window.localStorage : window.sessionStorage;
  const other = persist ? window.sessionStorage : window.localStorage;
  safeSet(other, STORAGE_KEYS.token, null);
  safeSet(target, STORAGE_KEYS.token, token);
}

/**
 * Remove every trace of the session from storage.
 *
 * @returns {void}
 */
export function clearStoredSession() {
  authToken = null;
  for (const storage of [window.localStorage, window.sessionStorage]) {
    safeSet(storage, STORAGE_KEYS.token, null);
    safeSet(storage, STORAGE_KEYS.user, null);
  }
}

/**
 * Turn an axios failure into a normalized, displayable error.
 *
 * Prefers the API error envelope (`{ message, error, code, errors }`) and falls
 * back to the HTTP status copy in {@link ERROR_MESSAGES}, then to a generic
 * message. Validation failures (422) are also flattened into `fieldErrors`.
 *
 * @param {unknown} error The rejected value from an axios call.
 * @returns {ApiError} Normalized error, always with a `message` and a `code`.
 *
 * @example
 * try {
 *   await api.post('/api/auth/login', credentials);
 * } catch (error) {
 *   const { status, message, fieldErrors } = handleApiError(error);
 *   if (fieldErrors.email) showInline(fieldErrors.email);
 *   else showToast(`${message} (${status})`);
 * }
 */
export function handleApiError(error) {
  /** @type {any} */
  const axiosError = error ?? {};
  const response = axiosError.response;
  const status = typeof response?.status === 'number' ? response.status : null;
  const body = response?.data && typeof response.data === 'object' ? response.data : {};
  const issues = Array.isArray(body.errors) ? body.errors : [];

  if (axiosError.code === 'ECONNABORTED' || /timeout/i.test(axiosError.code ?? '')) {
    return {
      status,
      code: 'timeout',
      message: TIMEOUT_ERROR_MESSAGE,
      details: '',
      issues: [],
      fieldErrors: {},
    };
  }

  if (!response) {
    return {
      status: null,
      code: axiosError.code || 'network_error',
      message: NETWORK_ERROR_MESSAGE,
      details: axiosError.message || '',
      issues: [],
      fieldErrors: {},
    };
  }

  return {
    status,
    code: body.code || `http_${status}`,
    message: body.message || ERROR_MESSAGES[status] || ERROR_MESSAGES[500],
    details: body.error || body.detail || '',
    issues: issues.map((issue) => `${issue.loc?.slice(-1)[0] ?? 'value'}: ${issue.msg}`),
    fieldErrors: issues.reduce((accumulator, issue) => {
      const field = issue.loc?.slice(-1)[0];
      if (field) accumulator[field] = issue.msg;
      return accumulator;
    }, {}),
  };
}

/**
 * Notify the registered handler about a failed request.
 *
 * @param {ApiEvent} event Status, code and message of the failure.
 * @returns {void}
 */
function emit(event) {
  if (!eventHandler) return;
  try {
    if (event.isUnauthorized) {
      eventHandler.onUnauthorized?.(event);
    } else {
      eventHandler.onError?.(event);
    }
  } catch {
    /* a broken handler must never mask the original request failure */
  }
}

/**
 * Redirect to the login page after the session was cleared.
 *
 * Uses the registered handler when the application provides one; outside a
 * router (tests, non-browser runtimes) it falls back to a full page load.
 *
 * @returns {void}
 */
function redirectToLogin() {
  const onLoginPage =
    typeof window !== 'undefined' && window.location?.pathname === ROUTES.login;
  if (onLoginPage) return;
  if (typeof window === 'undefined' || !window.location) return;
  window.location.replace(ROUTES.login);
}

/**
 * The shared axios instance.
 *
 * @type {import('axios').AxiosInstance}
 */
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Attach the bearer token to every outgoing request.
 *
 * Requests are marked so the response interceptor can tell an expired session
 * apart from a rejected sign-in attempt.
 *
 * @param {import('axios').InternalAxiosRequestConfig} config Outgoing request.
 * @returns {import('axios').InternalAxiosRequestConfig} The same config, with
 *   the `Authorization` header added when a token is available.
 */
api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Enrich and re-throw failures, applying the per-status policy.
 *
 * `meta.skipAuthHandling` marks the login and register calls: a wrong password
 * must not sign the user out or bounce them away from the login form.
 *
 * @param {unknown} error The rejected value from an axios call.
 * @returns {Promise<never>} Always rejects, with the enriched error.
 */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const normalized = handleApiError(error);
    error.status = normalized.status;
    error.code = normalized.code;
    error.userMessage = normalized.message;
    error.fieldErrors = normalized.fieldErrors;
    error.issues = normalized.issues;

    const skipAuthHandling = error.config?.meta?.skipAuthHandling === true;
    const skipAuthRedirect = error.config?.meta?.skipAuthRedirect === true;

    if (normalized.status === 401 && !skipAuthHandling) {
      clearStoredSession();
      if (!skipAuthRedirect) {
        emit({ ...normalized, isUnauthorized: true });
        redirectToLogin();
      }
      return Promise.reject(error);
    }

    if (REPORTED_STATUSES.includes(normalized.status)) {
      emit({ ...normalized, isUnauthorized: false });
    }
    return Promise.reject(error);
  },
);

export { api as default };