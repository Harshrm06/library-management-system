/**
 * Book catalog service.
 *
 * Wraps the book endpoints in `backend/app/routes/book_routes.py`. Every function
 * follows the rules the rest of the service layer uses:
 *
 * * it never throws - transport failures, timeouts and HTTP errors all become a
 *   structured {@link ServiceResult} so callers branch without try/catch,
 * * it returns `{ success, data, error, message }`, where `message` is always safe
 *   to render and `error` carries `{ status, code, message, details, issues,
 *   fieldErrors }`,
 * * blank search terms and filters are omitted rather than sent empty.
 *
 * Two deliberate choices are worth knowing about.
 *
 * **Pages, not offsets.** The API pages by offset (`skip`/`limit`) but answers with
 * a 1-based `page`. Callers think in pages, so `getAllBooks()` accepts either a
 * page or an offset and converts here, in one place. That is why the parameter is
 * documented as "first page-like argument" rather than just `skip`.
 *
 * **A stale fallback.** A failed list request is retried once from the last
 * successful response for the same query and returned with `data.stale: true`.
 * A brief network blip should not empty a catalog the reader is looking at, and
 * the flag tells the UI to say the copy counts may be out of date. Nothing is ever
 * served stale without that flag.
 *
 * Write functions (`createBook`, `updateBook`, `deleteBook`) require an admin
 * token; the request interceptor attaches it and a 403 is reported, not thrown.
 *
 * @example
 * // Positional, as the API expects:
 * const result = await getAllBooks(0, 10, 'dune', 'Science fiction');
 * if (result.success) setBooks(result.data.books);
 *
 * @example
 * // Or page-oriented, which is usually what a UI wants:
 * const { success, data } = await getAllBooks({ page: 3, pageSize: 20 });
 * if (success) setTotalPages(data.totalPages);
 *
 * @example
 * // Errors are data, not exceptions:
 * const { success, error } = await getBookById(999);
 * if (!success && error.status === 404) navigate(ROUTES.catalog);
 */

import api, { handleApiError } from './api';
import { BOOK_ENDPOINTS, PAGINATION } from '../utils/constants';

/**
 * @typedef {import('./api').ServiceResult} ServiceResult
 * @typedef {import('./api').ApiError} ApiError
 *
 * @typedef {object} Book
 * @property {number} id Primary key.
 * @property {string} title Book title.
 * @property {string} author Primary author.
 * @property {string} isbn Normalized ISBN digits.
 * @property {string|null} [genre] Genre.
 * @property {string|null} [description] Synopsis.
 * @property {number} [total_quantity] Copies owned.
 * @property {number} [available_quantity] Copies not on loan.
 * @property {number|null} [published_year] Year of first publication.
 * @property {boolean} [is_available] Derived availability flag.
 * @property {string} [created_at] UTC creation timestamp.
 * @property {string|null} [updated_at] UTC timestamp of the last edit.
 */

/**
 * @typedef {object} BookListResult
 * @property {Book[]} books Books on the requested page.
 * @property {number} total Total books matching the query.
 * @property {number} page 1-based page number.
 * @property {number} pageSize Page size.
 * @property {number} totalPages Total pages, never below 1.
 * @property {boolean} hasNext True when another page follows.
 * @property {boolean} [stale] True when this came from the fallback cache.
 */

/**
 * @typedef {object} AvailabilityResult
 * @property {boolean} available True when at least one copy can be borrowed.
 * @property {number} quantity Copies currently not on loan.
 * @property {number} totalQuantity Copies owned.
 */

/** Milliseconds of quiet before a debounced search sends its request. */
export const DEFAULT_SEARCH_DEBOUNCE_MS = 300;

/** How many list responses to retain for the stale fallback. */
const CACHE_LIMIT = 12;

/**
 * Last successful list response per query signature.
 *
 * @type {Map<string, BookListResult>}
 */
const listCache = new Map();

/**
 * Read the payload out of a response, whether or not it uses the envelope.
 *
 * The book routes return the model directly; the auth routes wrap it in
 * `{ success, message, data }`. Accepting both keeps this service correct if the
 * catalog later grows the envelope for consistency.
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
 * Form state uses camelCase while the API uses snake_case, so accepting both keeps
 * callers free of translation code.
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
 * Build a stable key for a query so equivalent requests share a cache entry.
 *
 * @param {{skip: number, limit: number, search?: string, genre?: string, sortBy?: string, sortOrder?: string}} query
 *   Normalized query parameters.
 * @returns {string} A cache key.
 */
function cacheKey(query) {
  return [
    query.skip,
    query.limit,
    query.search ?? '',
    query.genre ?? '',
    query.sortBy ?? '',
    query.sortOrder ?? '',
  ].join('|');
}

/**
 * Remember a successful list response, evicting the oldest entry when full.
 *
 * @param {string} key Cache key from {@link cacheKey}.
 * @param {BookListResult} result The response to retain.
 * @returns {void}
 */
function rememberResult(key, result) {
  // Re-insert so the key moves to the end and the oldest entry is evicted first.
  listCache.delete(key);
  listCache.set(key, result);
  while (listCache.size > CACHE_LIMIT) {
    const oldest = listCache.keys().next().value;
    listCache.delete(oldest);
  }
}

/**
 * Empty the list-response cache.
 *
 * Called after any write that may have changed the catalog. Also exported for
 * callers that need to guarantee fresh copy counts, e.g. after returning a book
 * from a screen that has one cached.
 *
 * @returns {void}
 *
 * @example
 * await createBook(payload);
 * clearBookCache();
 */
export function clearBookCache() {
  listCache.clear();
}

/**
 * Decide whether a failed write leaves the cached catalog trustworthy.
 *
 * A 4xx is a definite rejection - nothing changed - so the cache stands and the
 * reader keeps their list. A transport failure is different: the request may have
 * been applied before the connection dropped, so serving the pre-write catalog
 * could contradict the server. Those cases drop the cache.
 *
 * @param {ApiError} error The normalized failure.
 * @returns {boolean} True when the cache should be discarded.
 */
function writeOutcomeUnknown(error) {
  return !error?.status;
}

/**
 * Normalize the two accepted `getAllBooks` call styles into one query.
 *
 * Supports `getAllBooks({ page, pageSize, search, genre })` and
 * `getAllBooks(skip, limit, search, genre, { sortBy, sortOrder })`. The object form
 * is detected by its first argument, so existing page components keep working.
 *
 * @param {number|object} [skipOrOptions] Rows to skip, or an options object.
 * @param {number} [limit] Page size when called positionally.
 * @param {string} [search] Search term when called positionally.
 * @param {string} [genre] Genre filter when called positionally.
 * @param {{sortBy?: string, sortOrder?: string}} [extra] Sorting options.
 * @returns {{skip: number, limit: number, search?: string, genre?: string, sortBy?: string, sortOrder?: string}}
 *   Query parameters, with blanks removed.
 *
 * @example
 * normalizeQuery({ page: 2, pageSize: 20 }); // { skip: 20, limit: 20 }
 * normalizeQuery(0, 10, 'dune');             // { skip: 0, limit: 10, search: 'dune' }
 */
function normalizeQuery(skipOrOptions, limit, search, genre, extra) {
  if (skipOrOptions && typeof skipOrOptions === 'object') {
    const options = skipOrOptions;
    const pageSize = options.pageSize ?? PAGINATION.defaultPageSize;
    const page = Math.max(1, options.page ?? 1);
    return {
      skip: (page - 1) * pageSize,
      limit: pageSize,
      search: options.search?.trim() || undefined,
      genre: options.genre?.trim() || undefined,
      sortBy: options.sortBy || undefined,
      sortOrder: options.sortOrder || undefined,
    };
  }

  const skip = Math.max(0, Number(skipOrOptions) || 0);
  const pageSize = Math.max(1, Number(limit) || PAGINATION.defaultPageSize);
  return {
    skip,
    limit: pageSize,
    search: search?.trim() || undefined,
    genre: genre?.trim() || undefined,
    sortBy: extra?.sortBy || undefined,
    sortOrder: extra?.sortOrder || undefined,
  };
}

/**
 * Fetch one page of the catalog.
 *
 * `search` matches title, author or ISBN case-insensitively; `genre` is an exact,
 * case-insensitive match. Unknown genres simply return no matches rather than an
 * error.
 *
 * @param {number|{page?: number, pageSize?: number, search?: string, genre?: string, sortBy?: string, sortOrder?: string}} [skipOrOptions]
 *   Rows to skip, or an options object `{ page, pageSize, search, genre, sortBy, sortOrder }`.
 * @param {number} [limit] Page size, 1-100; defaults to 10.
 * @param {string} [search] Search term for title, author or ISBN.
 * @param {string} [genre] Exact genre filter.
 * @param {{sortBy?: string, sortOrder?: string}} [extra] Sorting options.
 * @returns {Promise<ServiceResult>} On success `data` is a {@link BookListResult}.
 *   A validation problem answers 422; a network failure falls back to the last
 *   good response for the same query with `data.stale: true` when one exists.
 *
 * @example
 * const { success, data } = await getAllBooks(0, 10, 'dune');
 * if (success) setTotal(data.total);
 *
 * @example
 * // Typed as an object when the offset is not what you care about:
 * const { data } = await getAllBooks({ page: 3, pageSize: 20, genre: 'Fantasy' });
 * if (data.stale) showStaleNotice();
 */
export async function getAllBooks(skipOrOptions, limit, search, genre, extra) {
  const query = normalizeQuery(skipOrOptions, limit, search, genre, extra);
  const key = cacheKey(query);

  const params = {
    skip: query.skip,
    limit: query.limit,
    search: query.search,
    genre: query.genre,
    sort_by: query.sortBy,
    sort_order: query.sortOrder,
  };

  try {
    const response = await api.get(BOOK_ENDPOINTS.list, { params });
    const payload = unwrapPayload(response);
    const books = Array.isArray(payload.books) ? payload.books : [];
    const total = Number.isFinite(payload.total) ? payload.total : books.length;

    /** @type {BookListResult} */
    const result = {
      books,
      total,
      page: query.limit ? Math.floor(query.skip / query.limit) + 1 : 1,
      pageSize: query.limit,
      // Never below 1, so an empty catalog still reports one (empty) page.
      totalPages: Math.max(1, Math.ceil(total / query.limit)),
      // Prefer the server's flag; fall back to arithmetic if it is absent.
      hasNext:
        typeof payload.has_next === 'boolean'
          ? payload.has_next
          : query.skip + books.length < total,
    };

    rememberResult(key, result);
    return ok(result, 'Catalog loaded');
  } catch (error) {
    const cached = listCache.get(key);
    if (cached) {
      const notice = 'Showing the last known catalog; the library service is unreachable.';
      return ok({ ...cached, stale: true }, notice);
    }
    return fail(error, 'The catalog could not be loaded.');
  }
}

/**
 * Fetch a single catalog entry.
 *
 * @param {number|string} bookId Primary key of the book.
 * @returns {Promise<ServiceResult>} On success `data` is `{ book }`. An unknown id
 *   fails with status 404 and code `book_not_found`.
 *
 * @example
 * const { success, data, error } = await getBookById(bookId);
 * if (error?.status === 404) setNotFound(true);
 * else if (success) setBook(data.book);
 */
export async function getBookById(bookId) {
  try {
    const response = await api.get(BOOK_ENDPOINTS.detail(bookId));
    return ok({ book: unwrapPayload(response) }, 'Book loaded');
  } catch (error) {
    return fail(error, 'That book could not be loaded.');
  }
}

/**
 * Add a book to the catalog. Admin only.
 *
 * Hyphens are stripped from `isbn` and it must be a valid ISBN-10 or ISBN-13 that
 * no other entry uses. When `available_quantity` is omitted the API sets it to
 * `total_quantity`, so it is only sent when the caller supplied one.
 *
 * `role` and `is_available` are never sent: the API does not accept them and would
 * reject the whole payload.
 *
 * @param {{
 *   title: string,
 *   author: string,
 *   isbn: string,
 *   total_quantity: number,
 *   available_quantity?: number,
 *   genre?: string,
 *   description?: string,
 *   published_year?: number,
 * }} bookData The new entry. Name and quantity fields may be camelCase.
 * @returns {Promise<ServiceResult>} On success `data` is `{ book }`. A duplicate
 *   ISBN fails with 409 and code `isbn_taken`; a non-admin caller gets 403; invalid
 *   input gets 422 with `error.fieldErrors` keyed by field.
 *
 * @example
 * const result = await createBook({ title: 'Dune', author: 'Frank Herbert',
 *   isbn: '9780441013593', totalQuantity: 3 });
 * if (!result.success && result.error.fieldErrors.isbn) {
 *   setErrors(result.error.fieldErrors);
 * }
 */
export async function createBook(bookData) {
  const payload = buildBookPayload(bookData);
  try {
    const response = await api.post(BOOK_ENDPOINTS.list, payload, {
      meta: { skipAuthRedirect: true },
    });
    clearBookCache();
    return ok(
      { book: unwrapPayload(response) },
      envelopeMessage(response, 'Book added to the catalog'),
    );
  } catch (error) {
    const result = fail(error, 'The book could not be added.');
    if (writeOutcomeUnknown(result.error)) clearBookCache();
    return result;
  }
}

/**
 * Apply a partial update to a catalog entry. Admin only.
 *
 * Only the fields present in `bookData` are sent, so omitted values keep their
 * stored content. Sending an unknown field would be rejected by the API, which
 * forbids extra keys.
 *
 * @param {number|string} bookId Primary key of the book.
 * @param {Partial<{
 *   title: string, author: string, isbn: string, genre: string,
 *   description: string, total_quantity: number, available_quantity: number,
 *   published_year: number,
 * }>} bookData Fields to change.
 * @returns {Promise<ServiceResult>} On success `data` is `{ book }`. An unknown id
 *   answers 404, a taken ISBN 409, inconsistent quantities 422.
 *
 * @example
 * await updateBook(book.id, { available_quantity: 3 });
 */
export async function updateBook(bookId, bookData) {
  const payload = buildBookPayload(bookData, { partial: true });
  try {
    const response = await api.put(BOOK_ENDPOINTS.detail(bookId), payload, {
      meta: { skipAuthRedirect: true },
    });
    clearBookCache();
    return ok({ book: unwrapPayload(response) }, envelopeMessage(response, 'Book updated'));
  } catch (error) {
    const result = fail(error, 'The book could not be updated.');
    if (writeOutcomeUnknown(result.error)) clearBookCache();
    return result;
  }
}

/**
 * Remove a book from the catalog. Admin only.
 *
 * The API refuses deletion while copies are on loan and answers 422 with code
 * `book_has_active_borrowings`, so an admin learns to return the copies first
 * rather than being told the delete "failed".
 *
 * @param {number|string} bookId Primary key of the book.
 * @returns {Promise<ServiceResult>} On success `data` is `{ id, message }`.
 *
 * @example
 * const { success, error } = await deleteBook(id);
 * if (error?.code === 'book_has_active_borrowings') setError(error.details);
 */
export async function deleteBook(bookId) {
  try {
    const response = await api.delete(BOOK_ENDPOINTS.detail(bookId), {
      meta: { skipAuthRedirect: true },
    });
    clearBookCache();
    const payload = unwrapPayload(response);
    return ok(
      { id: Number(bookId), message: payload.message ?? 'Book deleted successfully' },
      envelopeMessage(response, payload.message ?? 'Book deleted successfully'),
    );
  } catch (error) {
    const result = fail(error, 'The book could not be deleted.');
    if (writeOutcomeUnknown(result.error)) clearBookCache();
    return result;
  }
}

/**
 * Check whether a book can be borrowed right now.
 *
 * Cheaper than {@link getBookById}: a single row read that answers the question
 * the borrow flow asks before it starts.
 *
 * @param {number|string} bookId Primary key of the book.
 * @returns {Promise<ServiceResult>} On success `data` is an
 *   {@link AvailabilityResult}. An unknown id answers 404.
 *
 * @example
 * const { success, data } = await checkAvailability(7);
 * if (success && !data.available) showOutOfStockNotice();
 */
export async function checkAvailability(bookId) {
  try {
    const response = await api.get(BOOK_ENDPOINTS.availability(bookId));
    const payload = unwrapPayload(response);
    /** @type {AvailabilityResult} */
    const availability = {
      available: Boolean(payload.available),
      quantity: Number(payload.quantity ?? 0),
      totalQuantity: Number(payload.total_quantity ?? 0),
    };
    return ok(availability, 'Availability checked');
  } catch (error) {
    return fail(error, 'Availability could not be checked.');
  }
}

/**
 * Alias of {@link checkAvailability}, kept for the earlier name.
 *
 * @param {number|string} bookId Primary key of the book.
 * @returns {Promise<ServiceResult>} See {@link checkAvailability}.
 */
export const getBookAvailability = checkAvailability;

/**
 * Wrap {@link getAllBooks} so rapid calls collapse into one request.
 *
 * Intended for a search box that calls the service directly rather than debouncing
 * its React state; components that debounce state should use `useDebounce`
 * instead, which avoids holding an intermediate value in the render tree.
 *
 * @param {number} [delay] Quiet period in milliseconds.
 * @returns {(...args: any[]) => Promise<ServiceResult | null>} A debounced
 *   `getAllBooks`. Resolves `null` for calls superseded before they were sent, and
 *   exposes `cancel()` to drop a pending call.
 *
 * @example
 * const search = createDebouncedSearch(300);
 * input.addEventListener('input', (e) => search(0, 10, e.target.value));
 */
export function createDebouncedSearch(delay = DEFAULT_SEARCH_DEBOUNCE_MS) {
  /** @type {ReturnType<typeof setTimeout> | null} */
  let timer = null;
  /** @type {((value: ServiceResult) => void) | null} */
  let resolveLatest = null;

  function debounced(...args) {
    return new Promise((resolve) => {
      if (timer) clearTimeout(timer);
      // The superseded call resolves null so its awaiter stops waiting instead of
      // applying an answer for a term the reader has already replaced.
      if (resolveLatest) resolveLatest(null);
      resolveLatest = resolve;

      timer = setTimeout(async () => {
        timer = null;
        const pending = resolveLatest;
        resolveLatest = null;
        const result = await getAllBooks(...args);
        pending?.(result);
      }, delay);
    });
  }

  debounced.cancel = () => {
    if (timer) clearTimeout(timer);
    timer = null;
    if (resolveLatest) resolveLatest(null);
    resolveLatest = null;
  };

  return debounced;
}

/**
 * Copy the writable book fields out of a caller-supplied object.
 *
 * Only fields the API accepts are forwarded: `extra="forbid"` on the request
 * schemas means a stray key such as `role` or `is_available` would fail the whole
 * request with 422. An empty payload is returned as-is so the API, not this
 * function, decides whether an empty update is acceptable.
 *
 * @param {Record<string, unknown>} bookData Caller-supplied fields.
 * @param {{partial?: boolean}} [options] `partial: true` keeps zero and empty
 *   values, which for an update mean "set this to zero/none" rather than "omit".
 * @returns {Record<string, unknown>} A payload the API will accept.
 */
function buildBookPayload(bookData, { partial = false } = {}) {
  if (!bookData || typeof bookData !== 'object') return {};

  const candidates = [
    ['title', 'title', 'title'],
    ['author', 'author', 'author'],
    ['isbn', 'isbn', 'isbn'],
    ['genre', 'genre', 'genre'],
    ['description', 'description', 'description'],
    ['total_quantity', 'totalQuantity', 'total_quantity'],
    ['available_quantity', 'availableQuantity', 'available_quantity'],
    ['published_year', 'publishedYear', 'published_year'],
  ];

  const payload = {};
  for (const [field, camelKey, snakeKey] of candidates) {
    const value = pick(bookData, camelKey, snakeKey);
    if (value === undefined) continue;
    // On create, blank and zero optional values are dropped so the API applies its
    // own defaults. On update they are meaningful, so they are kept.
    if (!partial && (value === '' || value === null)) continue;
    payload[field] = value;
  }
  return payload;
}

export default {
  getAllBooks,
  getBookById,
  createBook,
  updateBook,
  deleteBook,
  checkAvailability,
  getBookAvailability: checkAvailability,
  createDebouncedSearch,
  clearBookCache,
};
