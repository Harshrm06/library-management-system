import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import LoadingSpinner from '../components/LoadingSpinner';
import { adminService } from '../services/adminService';
import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

const EMPTY_FORM = {
  title: '',
  author: '',
  isbn: '',
  genre: '',
  published_year: new Date().getFullYear(),
  description: '',
  total_copies: 1,
  available_copies: 1,
};

export default function AdminBooksPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [skip, setSkip] = useState(0);
  const [total, setTotal] = useState(0);

  // Search & Filter
  const [search, setSearch] = useState('');
  const [genre, setGenre] = useState('');
  const [genreInput, setGenreInput] = useState('');

  // Modal & Form State
  const [showModal, setShowModal] = useState(false);
  const [editingBookId, setEditingBookId] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);



  // Delete confirmation
  const [deletingBook, setDeletingBook] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const limit = 10;

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate(ROUTES.unauthorized);
      return;
    }
    loadBooks();
  }, [user, navigate, skip, search, genre]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setGenre(genreInput);
      setSkip(0);
    }, 400);
    return () => clearTimeout(timer);
  }, [genreInput]);

  const loadBooks = async () => {
    try {
      setLoading(true);
      const data = await adminService.getBooks(skip, limit, search, genre);
      setBooks(data.items || data.books || []);
      setTotal(data.total || 0);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.message || err.userMessage || err.message || 'Failed to load book inventory');
      setBooks([]);
    } finally {
      setLoading(false);
    }
  };

  // Inventory stats calculated from current page / overall
  const stats = useMemo(() => {
    const totalTitles = total;
    const totalCopies = books.reduce((acc, b) => acc + (b.total_quantity || 0), 0);
    const availableCopies = books.reduce((acc, b) => acc + (b.available_quantity || 0), 0);
    const borrowedCopies = Math.max(0, totalCopies - availableCopies);
    return { totalTitles, totalCopies, availableCopies, borrowedCopies };
  }, [books, total]);

  const validateForm = () => {
    const errors = {};
    if (!formData.title.trim()) errors.title = 'Title is required';
    if (!formData.author.trim()) errors.author = 'Author is required';
    
    const cleanIsbn = formData.isbn.trim().replace(/-/g, '');
    if (!cleanIsbn) {
      errors.isbn = 'ISBN is required';
    } else if (!/^(?:\d{9}[\dXx]|\d{13})$/.test(cleanIsbn)) {
      errors.isbn = 'ISBN must be 10 or 13 digits (e.g. 9780140449136)';
    }

    if (!formData.genre.trim()) errors.genre = 'Genre is required';
    
    const totalCopies = Number(formData.total_copies);
    if (!totalCopies || totalCopies < 1) {
      errors.total_copies = 'Total quantity must be at least 1';
    }

    if (editingBookId) {
      const avail = Number(formData.available_copies);
      if (avail < 0) {
        errors.available_copies = 'Available quantity cannot be negative';
      } else if (avail > totalCopies) {
        errors.available_copies = `Available copies cannot exceed total copies (${totalCopies})`;
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleOpenCreate = () => {
    setEditingBookId(null);
    setFormData(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  };

  const handleOpenEdit = async (book) => {
    try {
      const fullBook = await adminService.getBookById(book.id);
      setFormData({
        title: fullBook.title || '',
        author: fullBook.author || '',
        isbn: fullBook.isbn || '',
        genre: fullBook.genre || '',
        published_year: fullBook.published_year || new Date().getFullYear(),
        description: fullBook.description || '',
        total_copies: fullBook.total_quantity || 1,
        available_copies: fullBook.available_quantity !== undefined ? fullBook.available_quantity : fullBook.total_quantity,
      });
      setEditingBookId(book.id);
      setFormErrors({});
      setShowModal(true);
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Failed to load book details for editing');
    }
  };

  const handleSubmitForm = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        title: formData.title.trim(),
        author: formData.author.trim(),
        isbn: formData.isbn.trim().replace(/-/g, ''),
        genre: formData.genre.trim(),
        published_year: formData.published_year ? Number(formData.published_year) : null,
        description: formData.description.trim(),
        total_quantity: Number(formData.total_copies),
      };

      if (editingBookId) {
        payload.available_quantity = Number(formData.available_copies);
        await adminService.updateBook(editingBookId, payload);
        setSuccess(`"${formData.title}" updated successfully.`);
      } else {
        await adminService.createBook(payload);
        setSuccess(`"${formData.title}" added to library inventory.`);
      }

      setShowModal(false);
      setFormData(EMPTY_FORM);
      setEditingBookId(null);
      loadBooks();
      setTimeout(() => setSuccess(null), 4000);
    } catch (err) {
      const resp = err.response?.data;
      const msg = resp?.message || resp?.detail || err.userMessage || err.message || 'Operation failed';
      setFormErrors(prev => ({ ...prev, api: msg }));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteBook = async () => {
    if (!deletingBook) return;

    setDeleteBusy(true);
    try {
      await adminService.deleteBook(deletingBook.id);
      setSuccess(`Book "${deletingBook.title}" deleted successfully.`);
      setDeletingBook(null);
      loadBooks();
      setTimeout(() => setSuccess(null), 4000);
    } catch (err) {
      const status = err.response?.status || err.error?.status;
      const resp = err.response?.data;
      if (status === 409 || resp?.code === 'book_has_active_loans') {
        setError(resp?.message || 'Cannot delete book: Copies of this book are currently borrowed or have active borrowing records.');
      } else {
        setError(resp?.message || err.userMessage || err.message || 'Failed to delete book.');
      }
      setDeletingBook(null);
      setTimeout(() => setError(null), 6000);
    } finally {
      setDeleteBusy(false);
    }
  };

  return (
    <main className="page-container">
      {/* Header & Controls */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold text-brand-900">Book Inventory Management</h1>
          <p className="mt-1 text-sm text-ink-600">
            Catalog inventory controls: create new titles, adjust stock quantities, and supervise catalog integrity.
          </p>
        </div>
        <button
          type="button"
          onClick={handleOpenCreate}
          className="btn-forest flex items-center gap-2 self-start sm:self-auto"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          <span>Add New Book</span>
        </button>
      </div>

      {/* Notifications */}
      {error && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800">
          <svg className="h-5 w-5 shrink-0 text-rose-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-sm font-medium">{error}</div>
        </div>
      )}

      {success && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-forest-300 bg-forest-50 p-4 text-forest-800">
          <svg className="h-5 w-5 shrink-0 text-forest-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-sm font-medium">{success}</div>
        </div>
      )}

      {/* Inventory Stat Cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="card p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">Total Titles</p>
          <p className="mt-1 text-2xl font-bold text-brand-900">{stats.totalTitles}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">Page Copies</p>
          <p className="mt-1 text-2xl font-bold text-ink-800">{stats.totalCopies}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-forest-700">Available</p>
          <p className="mt-1 text-2xl font-bold text-forest-700">{stats.availableCopies}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-700">On Loan</p>
          <p className="mt-1 text-2xl font-bold text-amber-700">{stats.borrowedCopies}</p>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="card mb-6 p-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label className="input-label" htmlFor="admin-search-input">Search Titles or Authors</label>
            <div className="relative">
              <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-ink-400">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </span>
              <input
                id="admin-search-input"
                type="text"
                placeholder="Search by title, author, or ISBN…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setSkip(0);
                }}
                className="w-full rounded-lg border border-cream-300 py-2 pl-9 pr-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
          <div>
            <label className="input-label" htmlFor="admin-genre-input">Filter Genre</label>
            <input
              id="admin-genre-input"
              type="text"
              placeholder="e.g. Fiction, History…"
              value={genreInput}
              onChange={(e) => setGenreInput(e.target.value)}
              className="w-full rounded-lg border border-cream-300 py-2 px-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
        </div>
      </div>

      {/* Books Table */}
      {loading && books.length === 0 ? (
        <LoadingSpinner />
      ) : books.length > 0 ? (
        <div className="card overflow-hidden p-0 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-cream-300 bg-cream-50 text-xs font-semibold uppercase tracking-wider text-ink-600">
                  <th className="px-5 py-3.5">ID</th>
                  <th className="px-5 py-3.5">Title & Author</th>
                  <th className="px-5 py-3.5">ISBN</th>
                  <th className="px-5 py-3.5">Genre</th>
                  <th className="px-5 py-3.5 text-center">Stock</th>
                  <th className="px-5 py-3.5 text-center">Status</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cream-200 text-sm">
                {books.map((book) => {
                  const isAvailable = (book.available_quantity ?? 0) > 0;
                  return (
                    <tr key={book.id} className="hover:bg-cream-50/60 transition-colors">
                      <td className="px-5 py-4 font-mono text-xs text-ink-500">#{book.id}</td>
                      <td className="px-5 py-4">
                        <div className="font-semibold text-ink-900">{book.title}</div>
                        <div className="text-xs text-ink-500">{book.author} {book.published_year ? `(${book.published_year})` : ''}</div>
                      </td>
                      <td className="px-5 py-4 font-mono text-xs text-ink-600">{book.isbn}</td>
                      <td className="px-5 py-4">
                        <span className="rounded-full bg-cream-200 px-2.5 py-0.5 text-xs font-medium text-ink-800">
                          {book.genre}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-center">
                        <span className="font-semibold text-ink-900">{book.available_quantity}</span>
                        <span className="text-xs text-ink-500"> / {book.total_quantity}</span>
                      </td>
                      <td className="px-5 py-4 text-center">
                        <span
                          className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            isAvailable
                              ? 'bg-forest-100 text-forest-800 border border-forest-300'
                              : 'bg-rose-100 text-rose-800 border border-rose-300'
                          }`}
                        >
                          {isAvailable ? 'In Stock' : 'Out of Stock'}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Edit */}
                          <button
                            type="button"
                            onClick={() => handleOpenEdit(book)}
                            className="rounded-lg border border-cream-300 bg-white px-2.5 py-1 text-xs font-semibold text-ink-700 hover:bg-cream-100 transition-colors"
                          >
                            Edit
                          </button>
                          {/* Delete */}
                          <button
                            type="button"
                            onClick={() => setDeletingBook(book)}
                            className="rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-100 transition-colors"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex flex-col sm:flex-row items-center justify-between border-t border-cream-300 px-5 py-3.5 gap-3 bg-cream-50/50">
            <span className="text-xs text-ink-600">
              Showing <span className="font-semibold">{total > 0 ? skip + 1 : 0}</span> to{' '}
              <span className="font-semibold">{Math.min(skip + limit, total)}</span> of{' '}
              <span className="font-semibold">{total}</span> titles
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setSkip(Math.max(0, skip - limit))}
                disabled={skip === 0}
                className="btn-secondary py-1.5 px-3 text-xs"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => skip + limit < total && setSkip(skip + limit)}
                disabled={skip + limit >= total}
                className="btn-secondary py-1.5 px-3 text-xs"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="card text-center py-12">
          <svg className="mx-auto h-12 w-12 text-ink-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <h3 className="mt-3 text-base font-semibold text-ink-800">No books found</h3>
          <p className="mt-1 text-sm text-ink-500">Try adjusting your search criteria or add a new book to the inventory.</p>
          <button
            type="button"
            onClick={handleOpenCreate}
            className="btn-forest mt-4"
          >
            Add Book
          </button>
        </div>
      )}

      {/* Create / Edit Book Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/60 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="relative w-full max-w-lg rounded-2xl border border-cream-300 bg-white p-6 shadow-elevation my-8">
            <div className="flex items-center justify-between border-b border-cream-200 pb-4 mb-4">
              <h2 className="text-xl font-serif font-bold text-brand-900">
                {editingBookId ? 'Edit Book Details' : 'Add New Book to Catalog'}
              </h2>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="rounded-lg p-1 text-ink-400 hover:bg-cream-100 hover:text-ink-700"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {formErrors.api && (
              <div className="mb-4 rounded-lg border border-rose-300 bg-rose-50 p-3 text-xs font-medium text-rose-800">
                {formErrors.api}
              </div>
            )}

            <form onSubmit={handleSubmitForm} className="space-y-4">
              <div>
                <label className="input-label" htmlFor="book-form-title">Title *</label>
                <input
                  id="book-form-title"
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g. The Great Gatsby"
                  className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                  required
                />
                {formErrors.title && <p className="mt-1 text-xs text-rose-600">{formErrors.title}</p>}
              </div>

              <div>
                <label className="input-label" htmlFor="book-form-author">Author *</label>
                <input
                  id="book-form-author"
                  type="text"
                  value={formData.author}
                  onChange={(e) => setFormData({ ...formData, author: e.target.value })}
                  placeholder="e.g. F. Scott Fitzgerald"
                  className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                  required
                />
                {formErrors.author && <p className="mt-1 text-xs text-rose-600">{formErrors.author}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="input-label" htmlFor="book-form-isbn">ISBN * (10 or 13 digits)</label>
                  <input
                    id="book-form-isbn"
                    type="text"
                    value={formData.isbn}
                    onChange={(e) => setFormData({ ...formData, isbn: e.target.value })}
                    placeholder="9780140449136"
                    className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                    required
                  />
                  {formErrors.isbn && <p className="mt-1 text-xs text-rose-600">{formErrors.isbn}</p>}
                </div>

                <div>
                  <label className="input-label" htmlFor="book-form-genre">Genre *</label>
                  <input
                    id="book-form-genre"
                    type="text"
                    value={formData.genre}
                    onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
                    placeholder="e.g. Classics, Sci-Fi"
                    className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                    required
                  />
                  {formErrors.genre && <p className="mt-1 text-xs text-rose-600">{formErrors.genre}</p>}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="input-label" htmlFor="book-form-year">Published Year</label>
                  <input
                    id="book-form-year"
                    type="number"
                    value={formData.published_year}
                    onChange={(e) => setFormData({ ...formData, published_year: e.target.value })}
                    className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="input-label" htmlFor="book-form-total">Total Copies *</label>
                  <input
                    id="book-form-total"
                    type="number"
                    min="1"
                    value={formData.total_copies}
                    onChange={(e) => setFormData({ ...formData, total_copies: e.target.value })}
                    className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                    required
                  />
                  {formErrors.total_copies && <p className="mt-1 text-xs text-rose-600">{formErrors.total_copies}</p>}
                </div>

                {editingBookId ? (
                  <div>
                    <label className="input-label" htmlFor="book-form-available">Available Copies</label>
                    <input
                      id="book-form-available"
                      type="number"
                      min="0"
                      value={formData.available_copies}
                      onChange={(e) => setFormData({ ...formData, available_copies: e.target.value })}
                      className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                    />
                    {formErrors.available_copies && <p className="mt-1 text-xs text-rose-600">{formErrors.available_copies}</p>}
                  </div>
                ) : null}
              </div>

              <div>
                <label className="input-label" htmlFor="book-form-description">Description (optional)</label>
                <textarea
                  id="book-form-description"
                  rows="3"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Summary or book overview…"
                  className="w-full rounded-lg border border-cream-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-cream-200">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-forest"
                >
                  {submitting ? 'Saving…' : editingBookId ? 'Update Book' : 'Add to Inventory'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingBook && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-rose-200 bg-white p-6 shadow-elevation">
            <div className="flex items-center gap-3 text-rose-600 mb-3">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h3 className="text-lg font-bold text-ink-900">Delete Book Confirmation</h3>
            </div>
            <p className="text-sm text-ink-600">
              Are you sure you want to delete <span className="font-semibold text-ink-900">&ldquo;{deletingBook.title}&rdquo;</span>?
            </p>
            <p className="mt-2 text-xs text-amber-700 bg-amber-50 p-2.5 rounded-lg border border-amber-200">
              Note: Books with active loans or circulation records cannot be deleted until all loans are settled.
            </p>
            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeletingBook(null)}
                className="btn-secondary"
                disabled={deleteBusy}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteBook}
                disabled={deleteBusy}
                className="btn-danger"
              >
                {deleteBusy ? 'Deleting…' : 'Delete Book'}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}