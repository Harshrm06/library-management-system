import api from './api.js';
import { ADMIN_ENDPOINTS } from '../utils/constants';

const unwrapPayload = (body) => {
  if (body?.data) return body.data;
  if (Array.isArray(body)) return body;
  return body || {};
};

export const adminService = {
  // Dashboard
  getDashboardStats() {
    return api.get(ADMIN_ENDPOINTS.DASHBOARD_STATS).then(r => unwrapPayload(r.data));
  },

  // Users
  getUsers(skip = 0, limit = 10) {
    return api.get(ADMIN_ENDPOINTS.USERS_LIST, { params: { skip, limit } }).then(r => unwrapPayload(r.data));
  },

  getUserById(userId) {
    return api.get(ADMIN_ENDPOINTS.USERS_DETAIL(userId)).then(r => unwrapPayload(r.data));
  },

  updateUserRole(userId, newRole) {
    return api.patch(ADMIN_ENDPOINTS.USERS_ROLE(userId), { role: newRole }).then(r => unwrapPayload(r.data));
  },

  deleteUser(userId) {
    return api.delete(ADMIN_ENDPOINTS.USERS_DETAIL(userId)).then(r => unwrapPayload(r.data));
  },

  // Books
  getBooks(skip = 0, limit = 10, search = '', genre = '') {
    return api.get(ADMIN_ENDPOINTS.BOOKS_LIST, {
      params: { skip, limit, search, genre }
    }).then(r => unwrapPayload(r.data));
  },

  getBookById(bookId) {
    return api.get(ADMIN_ENDPOINTS.BOOKS_DETAIL(bookId)).then(r => unwrapPayload(r.data));
  },

  createBook(bookData) {
    return api.post(ADMIN_ENDPOINTS.BOOKS_LIST, bookData).then(r => unwrapPayload(r.data));
  },

  updateBook(bookId, bookData) {
    return api.patch(ADMIN_ENDPOINTS.BOOKS_DETAIL(bookId), bookData).then(r => unwrapPayload(r.data));
  },

  deleteBook(bookId) {
    return api.delete(ADMIN_ENDPOINTS.BOOKS_DETAIL(bookId)).then(r => unwrapPayload(r.data));
  },

  // Borrowing History
  getBorrowingHistory(skip = 0, limit = 10, filters = {}) {
    const params = { skip, limit };
    if (filters.status) params.status = filters.status;
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    return api.get(ADMIN_ENDPOINTS.BORROWINGS_HISTORY, { params }).then(r => unwrapPayload(r.data));
  },
};

export default adminService;