import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import LoadingSpinner from '../components/LoadingSpinner';
import { adminService } from '../services/adminService';
import { useAuth } from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

export default function AdminBooksPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [skip, setSkip] = useState(0);
  const [total, setTotal] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [editingBook, setEditingBook] = useState(null);
  const [search, setSearch] = useState('');
  const [genre, setGenre] = useState('');
  const [genreInput, setGenreInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    author: '',
    isbn: '',
    genre: '',
    published_year: new Date().getFullYear(),
    description: '',
    total_copies: 1,
  });
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
    }, 500);
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
      setError(err.message || 'Failed to load books');
      setBooks([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'published_year' || name === 'total_copies' ? parseInt(value) : value,
    }));
  };

  const resetForm = () => {
    setFormData({
      title: '',
      author: '',
      isbn: '',
      genre: '',
      published_year: new Date().getFullYear(),
      description: '',
      total_copies: 1,
    });
    setEditingBook(null);
  };

  const handleOpenCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const handleOpenEdit = async (book) => {
    try {
      const fullBook = await adminService.getBookById(book.id);
      setFormData({
        title: fullBook.title,
        author: fullBook.author,
        isbn: fullBook.isbn,
        genre: fullBook.genre,
        published_year: fullBook.published_year,
        description: fullBook.description || '',
        total_copies: fullBook.total_quantity,
      });
      setEditingBook(book.id);
      setShowForm(true);
    } catch (err) {
      setError('Failed to load book details');
    }
  };

  const handleSubmitForm = async (e) => {
    e.preventDefault();

    // Validation
    if (!formData.title || !formData.author || !formData.isbn || !formData.genre || formData.total_copies < 1) {
      setError('Please fill all required fields');
      return;
    }

    try {
      setSubmitting(true);
      if (editingBook) {
        await adminService.updateBook(editingBook, formData);
        setSuccess('Book updated successfully');
      } else {
        await adminService.createBook(formData);
        setSuccess('Book created successfully');
      }
      setShowForm(false);
      resetForm();
      loadBooks();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message || 'Failed to save book');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteBook = async (bookId, bookTitle) => {
    if (!window.confirm(`Are you sure you want to delete "${bookTitle}"?`)) return;

    try {
      await adminService.deleteBook(bookId);
      setSuccess(`Book "${bookTitle}" deleted successfully`);
      loadBooks();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      const status = err.response?.status || err.error?.status;
      if (status === 409) {
        setError(err.response?.data?.message || err.message || 'Cannot delete: this book has active loans. Please wait for all copies to be returned.');
      } else {
        setError(err.message || 'Failed to delete book');
      }
    }
  };

  if (loading && books.length === 0) return <LoadingSpinner />;

  return (
    <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Book Management</h1>
          <button
            onClick={handleOpenCreate}
            className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded font-semibold"
          >
            + Add New Book
          </button>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6">
            {success}
          </div>
        )}

        {/* Search and Filter */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <input
            type="text"
            placeholder="Search by title or author..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSkip(0);
            }}
            className="px-4 py-2 border rounded"
          />
          <input
            type="text"
            placeholder="Filter by genre..."
            value={genreInput}
            onChange={(e) => setGenreInput(e.target.value)}
            className="px-4 py-2 border rounded"
          />
        </div>

        {/* Books Table */}
        {books.length > 0 ? (
          <>
            <div className="overflow-x-auto bg-white rounded-lg shadow">
              <table className="w-full">
                <thead className="bg-gray-100 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold">ID</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Title</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Author</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">ISBN</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Genre</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Total</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Available</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {books.map((book) => (
                    <tr key={book.id} className="border-b hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm">{book.id}</td>
                      <td className="px-6 py-4 text-sm font-medium">{book.title}</td>
                      <td className="px-6 py-4 text-sm">{book.author}</td>
                      <td className="px-6 py-4 text-sm">{book.isbn}</td>
                      <td className="px-6 py-4 text-sm">{book.genre}</td>
                      <td className="px-6 py-4 text-sm">{book.total_quantity}</td>
                      <td className="px-6 py-4 text-sm">{book.available_quantity}</td>
                      <td className="px-6 py-4 text-sm space-x-2">
                        <button
                          onClick={() => handleOpenEdit(book)}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteBook(book.id, book.title)}
                          className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex justify-between items-center mt-6">
              <button
                onClick={() => setSkip(Math.max(0, skip - limit))}
                disabled={skip === 0}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Showing {skip + 1}-{Math.min(skip + limit, total)} of {total}
              </span>
              <button
                onClick={() => skip + limit < total && setSkip(skip + limit)}
                disabled={skip + limit >= total}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded"
              >
                Next
              </button>
            </div>
          </>
        ) : (
          <p className="text-gray-600">No books found</p>
        )}

        {/* Form Modal */}
        {showForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full max-h-[90vh] overflow-y-auto">
              <h2 className="text-2xl font-bold mb-6">
                {editingBook ? 'Edit Book' : 'Add New Book'}
              </h2>
              <form onSubmit={handleSubmitForm}>
                <div className="mb-4">
                  <label className="block text-sm font-semibold mb-2">Title *</label>
                  <input
                    type="text"
                    name="title"
                    value={formData.title}
                    onChange={handleFormChange}
                    required
                    className="w-full px-4 py-2 border rounded"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-semibold mb-2">Author *</label>
                  <input
                    type="text"
                    name="author"
                    value={formData.author}
                    onChange={handleFormChange}
                    required
                    className="w-full px-4 py-2 border rounded"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-semibold mb-2">ISBN *</label>
                  <input
                    type="text"
                    name="isbn"
                    value={formData.isbn}
                    onChange={handleFormChange}
                    required
                    className="w-full px-4 py-2 border rounded"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-semibold mb-2">Genre *</label>
                  <input
                    type="text"
                    name="genre"
                    value={formData.genre}
                    onChange={handleFormChange}
                    required
                    className="w-full px-4 py-2 border rounded"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-semibold mb-2">Published Year</label>
                  <input
                    type="number"
                    name="published_year"
                    value={formData.published_year}
                    onChange={handleFormChange}
                    className="w-full px-4 py-2 border rounded"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-semibold mb-2">Description</label>
                  <textarea
                    name="description"
                    value={formData.description}
                    onChange={handleFormChange}
                    rows="3"
                    className="w-full px-4 py-2 border rounded"
                  />
                </div>
                <div className="mb-6">
                  <label className="block text-sm font-semibold mb-2">Total Copies *</label>
                  <input
                    type="number"
                    name="total_copies"
                    value={formData.total_copies}
                    onChange={handleFormChange}
                    min="1"
                    required
                    className="w-full px-4 py-2 border rounded"
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      setShowForm(false);
                      resetForm();
                    }}
                    className="px-4 py-2 border rounded hover:bg-gray-100"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded font-semibold"
                  >
                    {submitting ? 'Saving...' : editingBook ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    
  );
}