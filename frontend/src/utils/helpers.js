/**
 * Small formatting and general-purpose helpers.
 */

/**
 * Join conditional class names.
 *
 * @param {...(string|false|null|undefined)} values Class names.
 * @returns {string} Space separated class list.
 */
export function cx(...values) {
  return values.filter(Boolean).join(' ');
}

/**
 * Format an ISO date for display.
 *
 * @param {string|number|Date|null|undefined} value Date input.
 * @param {string} [fallback] Text used when the value cannot be parsed.
 * @returns {string} Formatted date, e.g. `12 Mar 2026`.
 */
export function formatDate(value, fallback = '—') {
  if (!value) return fallback;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

/**
 * Format an ISO timestamp for display.
 *
 * @param {string|number|Date|null|undefined} value Timestamp input.
 * @param {string} [fallback] Text used when the value cannot be parsed.
 * @returns {string} Formatted date and time.
 */
export function formatDateTime(value, fallback = '—') {
  if (!value) return fallback;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/**
 * Truncate text to a maximum length.
 *
 * @param {string} value Text to shorten.
 * @param {number} [maxLength] Maximum characters to keep.
 * @returns {string} Possibly truncated text.
 */
export function truncate(value, maxLength = 140) {
  if (typeof value !== 'string') return '';
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1).trimEnd()}…`;
}

/**
 * Build a Date `days` after `from`.
 *
 * Uses local midnight arithmetic rather than adding `days * 86400000` ms, because
 * a fixed millisecond offset lands on the previous day across a daylight-saving
 * boundary.
 *
 * @param {Date|number|string} [from] Starting point; defaults to now.
 * @param {number} [days] Days to add; may be negative.
 * @returns {Date} A new Date, never the input.
 *
 * @example
 * addDays(new Date(2026, 0, 1), 14).getDate(); // 15
 */
export function addDays(from = new Date(), days = 0) {
  const start = from instanceof Date ? from : new Date(from);
  const result = new Date(start.getTime());
  result.setDate(result.getDate() + days);
  return result;
}

/**
 * Format a date as `DD MMM YYYY`, e.g. `14 Feb 2026`.
 *
 * @param {Date|number|string|null|undefined} value Date input.
 * @param {string} [fallback] Text used when the value cannot be parsed.
 * @returns {string} Formatted date.
 *
 * @example
 * formatDateLong('2026-02-14T10:00:00'); // '14 Feb 2026'
 */
export function formatDateLong(value, fallback = '—') {
  if (!value) return fallback;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

/**
 * Format a UTC timestamp for display, tolerating a naive (timezone-less) value.
 *
 * `Book.created_at` is stored and returned without a zone offset, so
 * `new Date('2026-02-14T09:00:00')` would be read as local time. Appending `Z`
 * makes it UTC as intended, and leaves an already-qualified timestamp untouched.
 *
 * @param {string|number|Date|null|undefined} value Timestamp input.
 * @param {string} [fallback] Text used when the value cannot be parsed.
 * @returns {string} Formatted date and time.
 *
 * @example
 * formatUtcDateTime('2026-02-14T09:00:00'); // '14 Feb 2026, 09:00'
 */
export function formatUtcDateTime(value, fallback = '—') {
  if (!value) return fallback;
  if (value instanceof Date) return formatDateTime(value, fallback);

  const raw = String(value);
  const naiveIso = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(raw);
  const parsed = new Date(naiveIso ? `${raw}Z` : raw);
  if (Number.isNaN(parsed.getTime())) return fallback;
  return formatDateTime(parsed, fallback);
}

/**
 * Decode the payload of a JWT without verifying its signature.
 *
 * The client only needs the claims to know when the token expires; the server
 * remains the authority on validity.
 *
 * @param {string | null | undefined} token Encoded JWT.
 * @returns {object | null} The decoded payload, or null when it cannot be read.
 */
export function decodeJwtPayload(token) {
  if (typeof token !== 'string' || token.split('.').length !== 3) return null;
  try {
    const [, payload] = token.split('.');
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    const decoded = decodeURIComponent(
      // `globalThis.atob` exists in browsers and in Node 16+, so this helper
      // works outside the browser too.
      globalThis
        .atob(normalized)
        .split('')
        .map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
        .join(''),
    );
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

/**
 * Check whether a token is expired or about to expire.
 *
 * @param {string | null | undefined} token Encoded JWT.
 * @param {number} [skewSeconds] Treat the token as expired this many seconds early.
 * @returns {boolean} True when the token is expired, unreadable or missing.
 */
export function isTokenExpired(token, skewSeconds = 30) {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return true;
  return payload.exp * 1000 <= Date.now() + skewSeconds * 1000;
}

/**
 * Build initials from a person's name.
 *
 * @param {{ first_name?: string, last_name?: string, firstName?: string, lastName?: string }} user
 *   User object from the API.
 * @returns {string} Up to two uppercase initials.
 */
export function getInitials(user) {
  if (!user) return '';
  const first = user.first_name ?? user.firstName ?? '';
  const last = user.last_name ?? user.lastName ?? '';
  return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase() || '?';
}

/**
 * Normalise the API envelope into a predictable error shape.
 *
 * Thin wrapper kept for pages that render raw `api` calls; new code should use
 * `handleApiError` from `services/api`, which also covers timeouts, network
 * failures and per-field validation messages.
 *
 * @deprecated Prefer `handleApiError` from `services/api`.
 * @param {unknown} error Rejection from axios or a service call.
 * @returns {{ message: string, code: string, status: number }} Error details.
 */
export function toErrorDetails(error) {
  const payload = error?.response?.data ?? {};
  return {
    message: payload.message || payload.detail || error?.message || 'Something went wrong',
    code: payload.code || 'unexpected_error',
    status: error?.response?.status ?? 0,
  };
}
