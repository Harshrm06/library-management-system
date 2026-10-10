/**
 * Client-side validation helpers.
 *
 * These mirror `backend/app/utils/validators.py` so the UI can reject bad
 * input before a request is sent; the backend remains the authority.
 */

import { PASSWORD_MIN_LENGTH } from './constants';

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/;

/**
 * Check whether a value is a non-empty string.
 *
 * @param {unknown} value Value to test.
 * @returns {boolean} True when the value is a usable string.
 */
export function isRequired(value) {
  return typeof value === 'string' ? value.trim().length > 0 : Boolean(value);
}

/**
 * Validate an email address.
 *
 * @param {string} email Address to test.
 * @returns {boolean} True when the address looks well formed.
 */
export function isValidEmail(email) {
  if (typeof email !== 'string') return false;
  const candidate = email.trim();
  return candidate.length > 0 && candidate.length <= 255 && EMAIL_PATTERN.test(candidate);
}

/**
 * Validate a password against the API policy: at least 6 characters with at
 * least one letter and one digit.
 *
 * @param {string} password Password to test.
 * @returns {{ valid: boolean, message: string }} Result and reason.
 */
export function validatePassword(password) {
  if (typeof password !== 'string' || password.length === 0) {
    return { valid: false, message: 'Password is required' };
  }
  if (password.length < PASSWORD_MIN_LENGTH) {
    return {
      valid: false,
      message: `Password must be at least ${PASSWORD_MIN_LENGTH} characters long`,
    };
  }
  if (!/[A-Za-z]/.test(password)) {
    return { valid: false, message: 'Password must contain at least one letter' };
  }
  if (!/\d/.test(password)) {
    return { valid: false, message: 'Password must contain at least one number' };
  }
  return { valid: true, message: '' };
}

/**
 * Rules the password strength meter scores and the register form lists.
 *
 * The first three entries are the API policy (see `validatePassword`); the rest
 * only influence the strength label.
 *
 * @type {ReadonlyArray<{ id: string, label: string, test: (value: string) => boolean }>}
 */
export const PASSWORD_REQUIREMENTS = Object.freeze([
  {
    id: 'length',
    label: `At least ${PASSWORD_MIN_LENGTH} characters`,
    test: (value) => value.length >= PASSWORD_MIN_LENGTH,
  },
  { id: 'letter', label: 'Contains a letter', test: (value) => /[A-Za-z]/.test(value) },
  { id: 'number', label: 'Contains a number', test: (value) => /\d/.test(value) },
  { id: 'uppercase', label: 'Contains an uppercase letter', test: (value) => /[A-Z]/.test(value) },
  { id: 'symbol', label: 'Contains a symbol', test: (value) => /[^A-Za-z0-9]/.test(value) },
]);

/**
 * Score a password and describe which requirements it meets.
 *
 * The label is advisory only - acceptance is decided by {@link validatePassword}
 * so the meter and the API can never disagree about what is allowed.
 *
 * @param {string} password Password to score.
 * @returns {{ score: number, label: 'empty'|'weak'|'medium'|'strong', requirements: Array<{ id: string, label: string, met: boolean }> }}
 *   Score from 0-5, a label, and the per-requirement checklist.
 *
 * @example
 * scorePasswordStrength('secretpass1').label; // 'medium'
 */
export function scorePasswordStrength(password) {
  const value = typeof password === 'string' ? password : '';
  const requirements = PASSWORD_REQUIREMENTS.map((requirement) => ({
    id: requirement.id,
    label: requirement.label,
    met: value.length > 0 && requirement.test(value),
  }));
  const score = requirements.filter((requirement) => requirement.met).length;

  let label = 'empty';
  if (value.length > 0) {
    if (score <= 2) label = 'weak';
    else if (score <= 4) label = 'medium';
    else label = 'strong';
  }

  return { score, label, requirements };
}

/**
 * Check that the confirmation field matches the password.
 *
 * @param {string} password The chosen password.
 * @param {string} confirmation The repeated value.
 * @returns {string} An error message, or an empty string when they match.
 *
 * @example
 * validatePasswordConfirmation('secretpass1', 'secretpass1'); // ''
 */
export function validatePasswordConfirmation(password, confirmation) {
  if (!isRequired(confirmation)) return 'Please confirm your password';
  if (confirmation !== password) return 'Passwords do not match';
  return '';
}

/**
 * Validate the registration form as a whole.
 *
 * @param {{ first_name: string, last_name: string, email: string, password: string, confirmPassword?: string }} values
 *   Form values keyed by snake_case names. `confirmPassword` is checked only when
 *   the form provides it, so callers without the field keep working.
 * @returns {Record<string, string>} Field name to error message; empty when valid.
 */
export function validateRegistration(values) {
  const errors = {};
  if (!isRequired(values.first_name)) errors.first_name = 'First name is required';
  if (!isRequired(values.last_name)) errors.last_name = 'Last name is required';
  if (!isValidEmail(values.email)) errors.email = 'Enter a valid email address';
  const password = validatePassword(values.password);
  if (!password.valid) errors.password = password.message;
  if (values.confirmPassword !== undefined) {
    const confirmation = validatePasswordConfirmation(values.password, values.confirmPassword);
    if (confirmation) errors.confirmPassword = confirmation;
  }
  return errors;
}

/**
 * Validate the login form.
 *
 * @param {{ email: string, password: string }} values Form values.
 * @returns {Record<string, string>} Field name to error message; empty when valid.
 */
export function validateLogin(values) {
  const errors = {};
  if (!isValidEmail(values.email)) errors.email = 'Enter a valid email address';
  if (!isRequired(values.password)) errors.password = 'Password is required';
  return errors;
}
