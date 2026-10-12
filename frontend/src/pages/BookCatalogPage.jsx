/**
 * Book catalog page: search, filter and paginate the collection.
 *
 * Supports Members borrowing books directly from the catalog
 * with a live 14-day loan confirmation dialog.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import BookCard from '../components/BookCard';
import BorrowModal from '../components/BorrowModal';
import Skeleton from '../components/Skeleton';
import Toast from '../components/Toast';
import useDebounce from '../hooks/useDebounce';
import { useAuth } from '../hooks/useAuth';
import { getAllBooks } from '../services/bookService';
import borrowService from '../services/borrowService';
import { PAGINATION } from '../utils/constants';

const SEARCH_DEBOUNCE_MS = 300;

function buildPageItems(currentPage, totalPages) {
  if (totalPages <= 1) return [1];

  const pages = new Set([1, totalPages]);
  for (
    let page = currentPage - PAGINATION.pageWindow;
    page <= currentPage + PAGINATION.pageWindow;
    page += 1
  ) {
    if (page >= 1 && page <= totalPages) pages.add(page);
  }

  const sorted = [...pages].sort((a, b) => a - b);
  const items = [];
  let previous = 0;
  for (const page of sorted) {
    if (previous && page - previous > 1) items.push('left-ellipsis');
    items.push(page);
    previous = page;
  }
  return items;
}

export default function BookCatalogPage() {
  const { isAdmin } = useAuth();
  const [searchParams] = useSearchParams();
  const genreFromUrl = searchParams.get('genre') ?? '';

  const [books, setBooks] = useState([]);
  const [totalBooks, setTotalBooks] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(PAGINATION.defaultPageSize);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGenre, setSelectedGenre] = useState(genreFromUrl);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successToast, setSuccessToast] = useState('');

  // Borrow Modal State
  const [borrowTargetBook, setBorrowTargetBook] = useState(null);
  const [borrowingBusy, setBorrowingBusy] = useState(false);
  const [borrowModalError, setBorrowModalError] = useState('');
  const [borrowModalSuccess, setBorrowModalSuccess] = useState('');

  useEffect(() => {
    setSelectedGenre(genreFromUrl);
  }, [genreFromUrl]);

  const debouncedSearch = useDebounce(searchQuery.trim(), SEARCH_DEBOUNCE_MS);

  const totalPages = Math.max(1, Math.ceil(totalBooks / pageSize));
  const hasPrevious = currentPage > 1;
  const hasNext = currentPage < totalPages;

  const requestId = useRef(0);

  const fetchBooks = useCallback(async () => {
    const id = requestId.current + 1;
    requestId.current = id;

    setLoading(true);
    setError('');
    const result = await getAllBooks({
      page: currentPage,
      pageSize,
      search: debouncedSearch,
      genre: selectedGenre,
    });

    if (requestId.current !== id) return;

    setLoading(false);
    if (!result.success) {
      setBooks([]);
      setError(result.message);
      return;
    }

    setBooks(result.data.books);
    setTotalBooks(result.data.total);

    if (result.data.page > result.data.totalPages && result.data.totalPages > 0) {
      setCurrentPage(result.data.totalPages);
    }
  }, [currentPage, pageSize, debouncedSearch, selectedGenre]);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  function handleSearchChange(event) {
    setSearchQuery(event.target.value);
    setCurrentPage(1);
  }

  function handleGenreChange(event) {
    setSelectedGenre(event.target.value);
    setCurrentPage(1);
  }

  function goToPage(page) {
    setCurrentPage(Math.min(Math.max(1, page), totalPages));
  }

  function resetFilters() {
    setSearchQuery('');
    setSelectedGenre('');
    setCurrentPage(1);
  }

  const genres = useMemo(() => {
    const seen = new Set();
    for (const book of books) {
      if (book.genre) seen.add(book.genre);
    }
    if (selectedGenre) seen.add(selectedGenre);
    return [...seen].sort((a, b) => a.localeCompare(b));
  }, [books, selectedGenre]);

  // Borrow Flow
  const handleOpenBorrowModal = (book) => {
    if (isAdmin) return;
    setBorrowTargetBook(book);
    setBorrowModalError('');
    setBorrowModalSuccess('');
  };

  const handleConfirmBorrow = async () => {
    if (!borrowTargetBook) return;

    setBorrowingBusy(true);
    setBorrowModalError('');
    setBorrowModalSuccess('');

    try {
      const res = await borrowService.borrowBook(borrowTargetBook.id);
      if (res.success) {
        setBorrowModalSuccess(`Successfully borrowed "${borrowTargetBook.title}".`);
        setSuccessToast(`"${borrowTargetBook.title}" borrowed. You can find it under My Loans.`);
        fetchBooks();
        setTimeout(() => {
          setBorrowTargetBook(null);
          setBorrowingBusy(false);
          setBorrowModalSuccess('');
        }, 1200);
      } else {
        setBorrowModalError(res.message || 'Unable to borrow book.');
        setBorrowingBusy(false);
      }
    } catch (err) {
      setBorrowModalError(err.response?.data?.message || err.message || 'Borrowing request failed.');
      setBorrowingBusy(false);
    }
  };

  const hasFilters = Boolean(searchQuery) || Boolean(selectedGenre);
  const showEmptyState = !loading && books.length === 0;

  return (
    <main className="page-container">
      {/* Header */}
      <header className="mb-6">
        <h1 className="text-2xl font-serif font-bold text-brand-900">Library Catalog</h1>
        <p className="mt-1 text-sm text-ink-600">
          Discover titles in our collection. Available books can be checked out directly.
        </p>
      </header>

      {/* Search and Filters */}
      <section
        className="card mb-6 flex flex-col gap-3 sm:flex-row sm:items-end border-cream-300 bg-white"
        aria-label="Search and filter"
      >
        <div className="flex-1">
          <label className="input-label" htmlFor="catalog-search">
            Search Titles, Authors, or ISBN
          </label>
          <div className="relative">
            <span
              className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-ink-400"
              aria-hidden="true"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
            <input
              id="catalog-search"
              type="search"
              value={searchQuery}
              onChange={handleSearchChange}
              placeholder="e.g. Orwell, 1984, 978…"
              autoComplete="off"
              className="w-full rounded-lg border border-cream-300 py-2 pl-9 pr-3 text-sm focus:border-brand-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="sm:w-56">
          <label className="input-label" htmlFor="catalog-genre">
            Genre Filter
          </label>
          <select
            id="catalog-genre"
            value={selectedGenre}
            onChange={handleGenreChange}
            className="w-full rounded-lg border border-cream-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          >
            <option value="">All Genres</option>
            {genres.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </div>

        {hasFilters && (
          <button type="button" className="btn-secondary" onClick={resetFilters}>
            Clear
          </button>
        )}
      </section>

      {/* Toast Notifications */}
      {error && (
        <Toast
          severity="error"
          message={error}
          className="mb-4"
          onClose={() => setError('')}
        />
      )}
      {successToast && (
        <Toast
          severity="success"
          message={successToast}
          className="mb-4"
          onClose={() => setSuccessToast('')}
        />
      )}

      {loading ? (
        <Skeleton count={6} className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" />
      ) : null}

      {showEmptyState && (
        <div className="card text-center py-12">
          <svg className="mx-auto h-12 w-12 text-ink-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <h3 className="mt-3 text-base font-semibold text-ink-800">No books found</h3>
          <p className="mt-1 text-sm text-ink-500">
            {hasFilters ? 'No titles match your current search or genre filter.' : 'The catalog is currently empty.'}
          </p>
          {hasFilters && (
            <button type="button" className="btn-secondary mt-4" onClick={resetFilters}>
              Reset Filters
            </button>
          )}
        </div>
      )}

      {!loading && books.length > 0 && (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {books.map((book) => (
            <BookCard
              key={book.id}
              book={book}
              onBorrow={isAdmin ? null : handleOpenBorrowModal}
            />
          ))}
        </div>
      )}

      {/* Pagination Bar */}
      {!loading && totalBooks > 0 && (
        <nav
          className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-between border-t border-cream-300 pt-4"
          aria-label="Pagination"
        >
          <p className="text-sm text-ink-600">
            Page <span className="font-semibold">{currentPage}</span> of{' '}
            <span className="font-semibold">{totalPages}</span> &middot; {totalBooks}{' '}
            {totalBooks === 1 ? 'title' : 'titles'}
          </p>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              className="btn-secondary py-1.5 px-3 text-xs"
              onClick={() => goToPage(currentPage - 1)}
              disabled={!hasPrevious || loading}
            >
              Previous
            </button>

            <ul className="flex items-center gap-1">
              {buildPageItems(currentPage, totalPages).map((item) =>
                typeof item === 'number' ? (
                  <li key={item}>
                    <button
                      type="button"
                      onClick={() => goToPage(item)}
                      disabled={loading}
                      aria-current={item === currentPage ? 'page' : undefined}
                      className={
                        item === currentPage
                          ? 'h-8 w-8 rounded-lg bg-brand-700 text-xs font-semibold text-white'
                          : 'h-8 w-8 rounded-lg border border-cream-300 bg-white text-xs text-ink-700 hover:bg-cream-100'
                      }
                    >
                      {item}
                    </button>
                  </li>
                ) : (
                  <li key={item} className="px-1 text-xs text-ink-400">
                    &hellip;
                  </li>
                ),
              )}
            </ul>

            <button
              type="button"
              className="btn-secondary py-1.5 px-3 text-xs"
              onClick={() => goToPage(currentPage + 1)}
              disabled={!hasNext || loading}
            >
              Next
            </button>
          </div>
        </nav>
      )}

      {/* Live Borrow Confirmation Dialog */}
      {!isAdmin && (
        <BorrowModal
          book={borrowTargetBook}
          isOpen={Boolean(borrowTargetBook)}
          onClose={() => {
            setBorrowTargetBook(null);
            setBorrowModalError('');
            setBorrowModalSuccess('');
          }}
          onBorrow={handleConfirmBorrow}
          borrowing={borrowingBusy}
          error={borrowModalError}
          success={borrowModalSuccess}
        />
      )}
    </main>
  );
}
