/**
 * Borrowing service.
 *
 * Wraps the borrowing endpoints named in the PRD:
 *
 * * `POST /api/borrow`                 - borrow one copy of a book
 * * `POST /api/return`                 - return a borrowed copy
 * * `GET  /api/borrowing-history`      - the caller's own loans
 *
 * **These endpoints are not implemented on the backend yet.** Only
 * `/api/auth/*` and `/api/books/*` are mounted, so `borrowBook()` currently
 * returns a failure carrying the 404 from the server rather than a loan. The
 * service is written against the documented contract so the UI is complete and
 * starts working the moment the routes land, and it never throws, so a missing
 * endpoint degrades into a message instead of a crash.
 *
 * Every function follows the rules in `authService.js`: no throwing, and a
 * `{ success, data, error, message }` result whose `message` is always safe to
 * display.
 *
 * @example
 * const result = await borrowBook(7);
 * if (result.success) showToast(result.message);
 * else showToast(result.message); // e.g. "All copies are currently on loan."
 *
 * @example
 * // Never throws, so callers branch rather than try/catch:
 * const { success, error } = await borrowBook(bookId);
 * if (!success && error.status === 409) setAlreadyBorrowed(true);
 */

import api, { handleApiError } from './api';
import { BORROW_ENDPOINTS } from '../utils/constants';

/**
 * @typedef {import('./api').ServiceResult} ServiceResult
 * @typedef {import('./api').ApiError} ApiError
 */

/**
 * Read the payload out of a response, whether or not it uses the envelope.
 *
 * @param {import('axios').AxiosResponse} response The axios response.
 * @returns {object} The payload object.
 */
function unwrapPayload(response) {
  const body = response?.data;
  if (body && typeof body === 'object' && 'data' in body && body.data) return body.data;
  return body ?? {};
}

/**
 * Read a message out of a response envelope.
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
 * A 404 is called out separately because it currently means "the borrowing
 * endpoints are not implemented" rather than "you asked for the wrong thing";
 * the copy tells the reader which of the two it is.
 *
 * @param {unknown} error The rejected value from an axios call.
 * @param {string} fallback Message to use when the failure carries none.
 * @returns {ServiceResult} `{ success: false, data: null, error, message }`.
 */
function fail(error, fallback) {
  const normalized = handleApiError(error);
  const message =
    normalized.status === 404
      ? 'Borrowing is not available yet: the server has no borrowing endpoint.'
      : normalized.message || fallback;
  return { success: false, data: null, error: normalized, message };
}

/**
 * Borrow one copy of a book.
 *
 * The server decrements `available_quantity` and creates the loan in one
 * transaction; the caller must not decrement anything locally. The `skipAuthRedirect`
 * flag keeps a 401 from bouncing the reader to the login form mid-modal, since
 * the dialog needs to stay open to show the error.
 *
 * @param {number|string} bookId Primary key of the book.
 * @returns {Promise<ServiceResult>} On success `data` is `{ borrowingRecord }`.
 *   All copies on loan answers 400 or 409; borrowing a second copy of a title the
 *   caller already holds is rejected by the server.
 *
 * @example
 * const { success, data, error } = await borrowBook(bookId);
 * if (success) navigate(ROUTES.borrowingHistory);
 * else if (error.status === 400) setError('All copies are on loan.');
 */
export async function borrowBook(bookId) {
  try {
    const response = await api.post(
      BORROW_ENDPOINTS.borrow,
      { book_id: Number(bookId) },
      { meta: { skipAuthRedirect: true } },
    );
    const payload = unwrapPayload(response);
    return ok(
      {
        borrowingRecord: payload.borrowing_record ?? payload.record ?? payload,
        dueDate: payload.due_date ?? null,
      },
      envelopeMessage(response, 'Book borrowed successfully'),
    );
  } catch (error) {
    return fail(error, 'The book could not be borrowed.');
  }
}

/**
 * Return a borrowed copy.
 *
 * @param {number|string} borrowingRecordId Id of the loan being returned.
 * @returns {Promise<ServiceResult>} On success `data` is `{ borrowingRecord }`.
 *
 * @example
 * await returnBook(record.id);
 */
export async function returnBook(borrowingRecordId) {
  try {
    const response = await api.post(
      BORROW_ENDPOINTS.returnBook,
      { borrowing_record_id: Number(borrowingRecordId) },
      { meta: { skipAuthRedirect: true } },
    );
    const payload = unwrapPayload(response);
    return ok(
      { borrowingRecord: payload.borrowing_record ?? payload.record ?? payload },
      envelopeMessage(response, 'Book returned successfully'),
    );
  } catch (error) {
    return fail(error, 'The book could not be returned.');
  }
}

/**
 * Fetch the caller's own borrowing history.
 *
 * @returns {Promise<ServiceResult>} On success `data` is `{ records }`, newest
 *   loan first.
 *
 * @example
 * const { success, data } = await getMemberHistory();
 * if (success) setRecords(data.records);
 */
export async function getMemberHistory() {
  try {
    const response = await api.get(BORROW_ENDPOINTS.history);
    const payload = unwrapPayload(response);
    const records = Array.isArray(payload.records)
      ? payload.records
      : Array.isArray(payload.borrowing_records)
        ? payload.borrowing_records
        : Array.isArray(payload)
          ? payload
          : [];
    return ok({ records }, envelopeMessage(response, 'Borrowing history loaded'));
  } catch (error) {
    return fail(error, 'Your borrowing history could not be loaded.');
  }
}

/**
 * Report whether the caller already holds a loan of a given book.
 *
 * The detail page needs this to disable the Borrow button. There is no dedicated
 * endpoint for it, so it is answered from the history: a record with status
 * `BORROWED` for this book means the reader already has one out. Returns
 * `unknown: true` when the history cannot be read, so the page can leave the
 * button enabled and let the server be the authority rather than blocking a
 * legitimate borrow on a failed lookup.
 *
 * @param {number|string} bookId Primary key of the book.
 * @returns {Promise<{ alreadyBorrowed: boolean, unknown: boolean }>} The verdict.
 *
 * @example
 * const { alreadyBorrowed, unknown } = await hasActiveLoan(bookId);
 * if (alreadyBorrowed) setButtonState('borrowed');
 */
export async function hasActiveLoan(bookId) {
  const result = await getMemberHistory();
  if (!result.success) return { alreadyBorrowed: false, unknown: true };

  const target = Number(bookId);
  const alreadyBorrowed = result.data.records.some((record) => {
    const recordBookId = Number(record?.book_id ?? record?.book?.id ?? record?.bookId);
    const status = String(record?.status ?? '').toUpperCase();
    return recordBookId === target && status !== 'RETURNED';
  });
  return { alreadyBorrowed, unknown: false };
}

export default {
  borrowBook,
  returnBook,
  getMemberHistory,
  hasActiveLoan,
};


