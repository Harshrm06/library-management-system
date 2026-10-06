/**
 * Book catalog page: search, filter and paginate the collection.
 *
 * Data flows through `bookService.getAllBooks()`, which converts the 1-based page
 * number held here into the `skip`/`limit` offset the API expects. Typing is
 * debounced by 300ms, so the page re-renders on every keystroke but only settled
 * search terms reach the network.
 *
 * The genre list is derived from the books currently on screen rather than a
 * hardcoded enum: the API exposes an exact-match `genre` filter but no endpoint
 * enumerating genres, so inventing a list here would offer filters that return
 * nothing. The set grows as the user browses.
 *
 * @example
 * // Reaching page 3 with a search and filter applied.
 * <BookCatalogPage />
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import BookCard from '../components/BookCard';
import Skeleton from '../components/Skeleton';
import Toast from '../components/Toast';
import useDebounce from '../hooks/useDebounce';
import { getAllBooks } from '../services/bookService';
import { PAGINATION } from '../utils/constants';

/** Milliseconds of quiet before a search term is sent to the API. */
const SEARCH_DEBOUNCE_MS = 300;

/**
 * Build the list of page numbers to render, with ellipses for the gaps.
 *
 * Always shows the first and last page plus a window around the current one, so
 * the control stays a fixed width whether the catalog has 5 pages or 500.
 *
 * @param {number} currentPage The page being viewed.
 * @param {number} totalPages Total number of pages.
 * @returns {Array<number|'left-ellipsis'|'right-ellipsis'>} Renderable entries.
 */
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

/**
 * Render the catalog grid and its controls.
 *
 * @returns {JSX.Element} The page.
 */
export default function BookCatalogPage() {
  // The genre filter is mirrored in the query string so a book's genre badge can
  // deep-link into a pre-filtered catalog and the link is shareable.
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
  const [jumpValue, setJumpValue] = useState('');

  // Follow the URL when it changes, e.g. navigating back from a book page.
  useEffect(() => {
    setSelectedGenre(genreFromUrl);
  }, [genreFromUrl]);

  // Only a settled search term triggers a request.
  const debouncedSearch = useDebounce(searchQuery.trim(), SEARCH_DEBOUNCE_MS);

  const totalPages = Math.max(1, Math.ceil(totalBooks / pageSize));
  const hasPrevious = currentPage > 1;
  const hasNext = currentPage < totalPages;

  // Guards against a slow response for an old query overwriting a newer one.
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

    // A newer request has already started, so this answer is stale.
    if (requestId.current !== id) return;

    setLoading(false);
    if (!result.success) {
      setBooks([]);
      setError(result.message);
      return;
    }

    setBooks(result.data.books);
    setTotalBooks(result.data.total);

    // A search or filter can leave the reader past the last page (page 5 of 2),
    // so fall back to the final page rather than showing an empty grid.
    if (result.data.page > result.data.totalPages) {
      setCurrentPage(result.data.totalPages);
    }
  }, [currentPage, pageSize, debouncedSearch, selectedGenre]);

  // Mount, and every change to the query that affects the result set.
  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  // A new search or filter invalidates the current page number.
  function handleSearchChange(event) {
    setSearchQuery(event.target.value);
    setCurrentPage(1);
  }

  function handleGenreChange(event) {
    setSelectedGenre(event.target.value);
    setCurrentPage(1);
  }

  function handleJumpSubmit(event) {
    event.preventDefault();
    const requested = Number(jumpValue);
    setJumpValue('');
    if (!Number.isInteger(requested)) return;
    setCurrentPage(Math.min(Math.max(1, requested), totalPages));
  }

  function goToPage(page) {
    setCurrentPage(Math.min(Math.max(1, page), totalPages));
  }

  function resetFilters() {
    setSearchQuery('');
    setSelectedGenre('');
    setCurrentPage(1);
  }

  // Genres seen so far. Kept in a ref-free state update so the dropdown keeps
  // every option the reader has already browsed past.
  const genres = useMemo(() => {
    const seen = new Set();
    for (const book of books) {
      if (book.genre) seen.add(book.genre);
    }
    // The active filter must stay selectable even when it matches nothing.
    if (selectedGenre) seen.add(selectedGenre);
    return [...seen].sort((a, b) => a.localeCompare(b));
  }, [books, selectedGenre]);

  const hasFilters = Boolean(searchQuery) || Boolean(selectedGenre);
  const showEmptyState = !loading && books.length === 0;

  return (
    <main className="page-container">
      <header className="mb-6">
        <h1 className="text-2xl">Browse Books</h1>
        <p className="mt-1 text-sm text-ink-600">
          Search the collection by title, author or ISBN.
        </p>
      </header>

      <section
        className="card sticky top-16 z-10 mb-6 flex flex-col gap-3 sm:flex-row sm:items-end"
        aria-label="Search and filter"
      >
        <div className="flex-1">
          <label className="input-label" htmlFor="book-search">
            Search
          </label>
          <div className="relative">
            <span
              className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-ink-500"
              aria-hidden="true"
            >
              &#9906;
            </span>
            <input
              id="book-search"
              type="search"
              value={searchQuery}
              onChange={handleSearchChange}
              placeholder="Title, author or ISBN…"
              autoComplete="off"
              className="w-full rounded-lg border border-ink-300 py-2 pl-9 pr-3 text-sm"
            />
          </div>
        </div>

        <div className="sm:w-56">
          <label className="input-label" htmlFor="book-genre">
            Genre
          </label>
          <select
            id="book-genre"
            value={selectedGenre}
            onChange={handleGenreChange}
            className="w-full rounded-lg border border-ink-300 bg-white px-3 py-2 text-sm"
          >
            <option value="">All Genres</option>
            {genres.map((genre) => (
              <option key={genre} value={genre}>
                {genre}
              </option>
            ))}
          </select>
        </div>

        {hasFilters ? (
          <button type="button" className="btn-secondary" onClick={resetFilters}>
            Clear
          </button>
        ) : null}
      </section>

      <Toast
        severity="error"
        message={error}
        className="mb-4"
        onClose={() => setError('')}
      />

      <p className="sr-only" role="status" aria-live="polite">
        {loading
          ? 'Loading books'
          : `${totalBooks} ${totalBooks === 1 ? 'book' : 'books'} found`}
      </p>

      {loading ? <Skeleton count={6} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" /> : null}

      {showEmptyState ? (
        <div className="card text-center">
          <p className="text-ink-700">
            {hasFilters ? 'No books match your search or filter.' : 'No books found.'}
          </p>
          {hasFilters ? (
            <button type="button" className="btn-secondary mt-4" onClick={resetFilters}>
              Clear search and filters
            </button>
          ) : (
            <button type="button" className="btn-secondary mt-4" onClick={fetchBooks}>
              Try again
            </button>
          )}
        </div>
      ) : null}

      {!loading && books.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {books.map((book) => (
            <BookCard key={book.id} book={book} />
          ))}
        </div>
      ) : null}

      {!loading && totalBooks > 0 ? (
        <nav
          className="mt-6 flex flex-col items-center gap-3 sm:flex-row sm:justify-between"
          aria-label="Pagination"
        >
          <p className="text-sm text-ink-600">
            Page {currentPage} of {totalPages} &middot; {totalBooks}{' '}
            {totalBooks === 1 ? 'book' : 'books'}
          </p>

          <div className="flex flex-wrap items-center justify-center gap-2">
            <button
              type="button"
              className="btn-secondary"
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
                      aria-label={`Page ${item}`}
                      className={
                        item === currentPage
                          ? 'h-9 w-9 rounded-lg bg-brand-600 text-sm font-medium text-white'
                          : 'h-9 w-9 rounded-lg border border-ink-300 bg-white text-sm text-ink-800 hover:bg-ink-100'
                      }
                    >
                      {item}
                    </button>
                  </li>
                ) : (
                  <li
                    key={item}
                    className="px-1 text-sm text-ink-500"
                    aria-hidden="true"
                  >
                    &hellip;
                  </li>
                ),
              )}
            </ul>

            <button
              type="button"
              className="btn-secondary"
              onClick={() => goToPage(currentPage + 1)}
              disabled={!hasNext || loading}
            >
              Next
            </button>
          </div>

          <form className="flex items-end gap-2" onSubmit={handleJumpSubmit}>
            <div>
              <label className="input-label" htmlFor="page-jump">
                Go to page
              </label>
              <input
                id="page-jump"
                type="number"
                min={1}
                max={totalPages}
                value={jumpValue}
                onChange={(event) => setJumpValue(event.target.value)}
                placeholder={String(currentPage)}
                className="w-20 rounded-lg border border-ink-300 px-3 py-2 text-sm"
              />
            </div>
            <button type="submit" className="btn-secondary" disabled={loading}>
              Go
            </button>
          </form>
        </nav>
      ) : null}
    </main>
  );
}
