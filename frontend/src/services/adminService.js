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
  getUsers(skip = 0, limit = 10, search = '', role = '') {
    const page = Math.floor(skip / limit) + 1;
    const page_size = limit;
    const params = { page, page_size, skip, limit };
    if (search) params.search = search;
    if (role) params.role = role;
    return api.get(ADMIN_ENDPOINTS.USERS_LIST, { params }).then(r => unwrapPayload(r.data));
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

  createMember(userData) {
    const payload = { ...userData };
    return api.post(ADMIN_ENDPOINTS.USERS_LIST, payload).then(r => unwrapPayload(r.data));
  },

  createUser(userData) {
    return this.createMember(userData);
  },

  // Books
  getBooks(skip = 0, limit = 10, search = '', genre = '') {
    const page = Math.floor(skip / limit) + 1;
    const page_size = limit;
    const params = { page, page_size, skip, limit };
    if (search) params.search = search;
    if (genre) params.genre = genre;
    return api.get(ADMIN_ENDPOINTS.BOOKS_LIST, { params }).then(r => unwrapPayload(r.data));
  },

  getBookById(bookId) {
    return api.get(ADMIN_ENDPOINTS.BOOKS_DETAIL(bookId)).then(r => unwrapPayload(r.data));
  },

  createBook(bookData) {
    const payload = { ...bookData };
    if (payload.total_quantity === undefined && payload.total_copies !== undefined) {
      payload.total_quantity = Number(payload.total_copies);
    }
    if (payload.available_quantity === undefined && payload.available_copies !== undefined) {
      payload.available_quantity = Number(payload.available_copies);
    }
    delete payload.total_copies;
    delete payload.available_copies;
    if (payload.published_year !== undefined && payload.published_year !== null && payload.published_year !== '') {
      payload.published_year = Number(payload.published_year);
    } else {
      delete payload.published_year;
    }
    return api.post(ADMIN_ENDPOINTS.BOOKS_LIST, payload).then(r => unwrapPayload(r.data));
  },

  updateBook(bookId, bookData) {
    const payload = { ...bookData };
    if (payload.total_quantity === undefined && payload.total_copies !== undefined) {
      payload.total_quantity = Number(payload.total_copies);
    }
    if (payload.available_quantity === undefined && payload.available_copies !== undefined) {
      payload.available_quantity = Number(payload.available_copies);
    }
    delete payload.total_copies;
    delete payload.available_copies;
    if (payload.published_year !== undefined && payload.published_year !== null && payload.published_year !== '') {
      payload.published_year = Number(payload.published_year);
    } else if (payload.published_year === '') {
      payload.published_year = null;
    }
    return api.patch(ADMIN_ENDPOINTS.BOOKS_DETAIL(bookId), payload).then(r => unwrapPayload(r.data));
  },

  deleteBook(bookId) {
    return api.delete(ADMIN_ENDPOINTS.BOOKS_DETAIL(bookId)).then(r => unwrapPayload(r.data));
  },

  // Borrowing History
  getBorrowingHistory(skip = 0, limit = 10, filters = {}) {
    const page = Math.floor(skip / limit) + 1;
    const page_size = limit;
    const params = { page, page_size, skip, limit };
    if (filters.status) params.status = filters.status;
    const from = filters.from_date || filters.start_date;
    const to = filters.to_date || filters.end_date;
    if (from) {
      params.from_date = from;
      params.start_date = from;
    }
    if (to) {
      params.to_date = to;
      params.end_date = to;
    }
    if (filters.search) params.search = filters.search;
    if (filters.user_id) params.user_id = filters.user_id;
    return api.get(ADMIN_ENDPOINTS.BORROWINGS_HISTORY, { params }).then(r => unwrapPayload(r.data));
  },
};

export default adminService;