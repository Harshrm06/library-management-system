/**
 * Application-wide constants: API paths, roles, storage keys and routes.
 */

// `import.meta.env` is injected by Vite. The optional chain keeps the module
// importable outside the bundler (unit tests, SSR) where it is undefined.
export const API_BASE_URL =
  import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000';

export const API_PREFIX = '/api';

export const AUTH_ENDPOINTS = {
  register: `${API_PREFIX}/auth/register`,
  login: `${API_PREFIX}/auth/login`,
  me: `${API_PREFIX}/auth/me`,
  refreshToken: `${API_PREFIX}/auth/refresh-token`,
  logout: `${API_PREFIX}/auth/logout`,
};

export const BOOK_ENDPOINTS = {
  list: `${API_PREFIX}/books`,
  detail: (bookId) => `${API_PREFIX}/books/${bookId}`,
  availability: (bookId) => `${API_PREFIX}/books/${bookId}/availability`,
};

export const BORROW_ENDPOINTS = {
  borrow: `${API_PREFIX}/borrow`,
  returnBook: `${API_PREFIX}/return`,
  history: `${API_PREFIX}/borrowing-history`,
};

export const STORAGE_KEYS = {
  token: 'lms.token',
  user: 'lms.user',
  rememberMe: 'lms.rememberMe',
};

export const ROLES = {
  admin: 'admin',
  member: 'member',
};

export const ROUTES = {
  login: '/login',
  register: '/register',
  dashboard: '/dashboard',
  catalog: '/books',
  bookDetail: '/books/:bookId',
  borrowingHistory: '/borrowing-history',
  profile: '/profile',
  adminDashboard: '/admin',
  unauthorized: '/unauthorized',
  home: '/',
};

export const PAGINATION = {
  defaultPageSize: 10,
  // The API caps `limit` at 100; sending more is rejected with 422.
  maxPageSize: 100,
  // Page numbers shown around the current one before collapsing to an ellipsis.
  pageWindow: 2,
};

export const PASSWORD_MIN_LENGTH = 6;

/** Loan period in days, as fixed by the PRD. */
export const BORROW_PERIOD_DAYS = 14;
