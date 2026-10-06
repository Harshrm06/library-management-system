/**
 * Single book view.
 *
 * Reads the book through `bookService.getBookById()` so the screen always reflects
 * the server, and borrows through `borrowService.borrowBook()`. Availability is
 * read from `available_quantity`, with `is_available` used only as a fallback, so
 * the Borrow button turns itself off as soon as the last copy leaves the shelf.
 *
 * A 404 renders the shared `NotFoundPage`; any other failure keeps the page
 * structure and offers a retry, so a dropped connection does not look like a
 * missing book.
 *
 * @example
 * // A borrowed book returns the reader to their history.
 * <BookDetailPage />   // location = /books/7
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import BookCard from '../components/BookCard';
import BorrowModal from '../components/BorrowModal';
import Skeleton from '../components/Skeleton';
import Toast from '../components/Toast';
import NotFoundPage from './NotFoundPage';
import { getAllBooks, getBookById } from '../services/bookService';
import { borrowBook, hasActiveLoan } from '../services/borrowService';
import { ROUTES } from '../utils/constants';
import { cx, formatUtcDateTime } from '../utils/helpers';

/** How many related titles to look for. */
const RELATED_LIMIT = 3;

/**
 * Derive one or two initials for the cover placeholder.
 *
 * @param {{ title?: string }} book Book object.
 * @returns {string} Up to two uppercase letters.
 */
function titleInitials(book) {
  const words = String(book?.title ?? '')
    .split(/\s+/)
    .filter(Boolean);
  if (words.length === 0) return '?';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
}

/**
 * Render the detail skeleton, laid out like the loaded page so the swap does not
 * shift the content below it.
 *
 * @returns {JSX.Element} The placeholder.
 */
function DetailSkeleton() {
  return (
    <div className="grid gap-6 lg:grid-cols-[200px_1fr]">
      <Skeleton count={1} />
      <div>
        <Skeleton count={3} />
        <p className="sr-only" role="status" aria-live="polite">
          Loading book
        </p>
      </div>
    </div>
  );
}

/**
 * Render the book detail page.
 *
 * @returns {JSX.Element} The page.
 */
export default function BookDetailPage() {
  const { bookId } = useParams();
  const navigate = useNavigate();

  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notFound, setNotFound] = useState(false);
  const [showBorrowModal, setShowBorrowModal] = useState(false);
  const [borrowing, setBorrowing] = useState(false);
  const [borrowError, setBorrowError] = useState('');
  const [borrowSuccess, setBorrowSuccess] = useState('');
  const [related, setRelated] = useState([]);
  const [alreadyBorrowed, setAlreadyBorrowed] = useState(false);

  const fetchBook = useCallback(async () => {
    setLoading(true);
    setError('');
    setNotFound(false);

    const result = await getBookById(bookId);
    if (result.success) {
      setBook(result.data.book);
      setLoading(false);
      return;
    }

    setBook(null);
    setLoading(false);
    // A missing book and a broken request look the same to the reader unless the
    // page says which one it is.
    if (result.error?.status === 404) {
      setNotFound(true);
      return;
    }
    setError(result.message);
  }, [bookId]);

  useEffect(() => {
    fetchBook();
  }, [fetchBook]);

  // Related titles share an author or a genre; the list is decoration, so a
  // failure is ignored rather than surfaced.
  useEffect(() => {
    if (!book) return;
    let cancelled = false;

    async function loadRelated() {
      const genre = book.genre ? { genre: book.genre } : { search: book.author };
      const result = await getAllBooks({ page: 1, pageSize: RELATED_LIMIT + 1, ...genre });
      if (cancelled || !result.success) return;
      setRelated(result.data.books.filter((item) => item.id !== book.id).slice(0, RELATED_LIMIT));
    }

    loadRelated();
    return () => {
      cancelled = true;
    };
  }, [book]);

  // The server is the authority on whether this reader already holds a copy, but
  // a failed lookup must not disable a legitimate borrow.
  useEffect(() => {
    if (!book || (book.available_quantity ?? 0) <= 0) return;
    let cancelled = false;

    async function checkLoan() {
      const { alreadyBorrowed: held, unknown } = await hasActiveLoan(bookId);
      if (!cancelled && !unknown) setAlreadyBorrowed(held);
    }

    checkLoan();
    return () => {
      cancelled = true;
    };
  }, [book, bookId]);

  async function handleBorrow() {
    setBorrowing(true);
    setBorrowError('');
    setBorrowSuccess('');

    const result = await borrowBook(book.id);
    setBorrowing(false);

    if (!result.success) {
      setBorrowError(result.message);
      return;
    }

    setBorrowSuccess(result.message);
    // Success is announced in the dialog before navigating, so a screen reader
    // user is told what happened rather than silently moved.
    setTimeout(() => navigate(ROUTES.borrowingHistory), 1200);
  }

  if (notFound) {
    return <NotFoundPage />;
  }

  if (loading) {
    return (
      <main className="page-container">
        <DetailSkeleton />
      </main>
    );
  }

  if (error || !book) {
    return (
      <main className="page-container">
        <nav aria-label="Breadcrumb" className="mb-4 text-sm text-ink-500">
          <Link to={ROUTES.dashboard} className="text-ink-600">
            Home
          </Link>
          <span aria-hidden="true" className="px-2">
            /
          </span>
          <Link to={ROUTES.catalog} className="text-ink-600">
            Books
          </Link>
        </nav>

        <Toast
          severity="error"
          message={error || 'This book could not be loaded.'}
          className="mb-4"
          onClose={() => setError('')}
        />

        <div className="card text-center">
          <h1 className="text-lg">Something went wrong</h1>
          <p className="mt-2 text-sm text-ink-600">
            The book details could not be loaded from the library service.
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <button type="button" className="btn-primary" onClick={fetchBook}>
              Try again
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate(ROUTES.catalog)}
            >
              Back to catalog
            </button>
          </div>
        </div>
      </main>
    );
  }

  const available = book.available_quantity ?? 0;
  const total = book.total_quantity ?? 0;
  const isAvailable = book.is_available ?? available > 0;

  return (
    <main className="page-container">
      <nav aria-label="Breadcrumb" className="mb-4 text-sm text-ink-500">
        <Link to={ROUTES.dashboard} className="text-ink-600">
          Home
        </Link>
        <span aria-hidden="true" className="px-2">
          /
        </span>
        <Link to={ROUTES.catalog} className="text-ink-600">
          Books
        </Link>
        <span aria-hidden="true" className="px-2">
          /
        </span>
        <span aria-current="page" className="text-ink-900">
          {book.title}
        </span>
      </nav>

      <article className="card">
        <div className="grid gap-6 lg:grid-cols-[180px_1fr]">
          <div
            className="flex h-48 w-full items-center justify-center rounded-lg bg-ink-100 text-2xl font-semibold text-ink-500 lg:h-56"
            aria-hidden="true"
          >
            {titleInitials(book)}
          </div>

          <div>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h1 className="text-2xl lg:text-3xl">{book.title}</h1>
              <span
                className={cx(
                  'rounded-full px-3 py-1 text-xs font-medium',
                  isAvailable ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800',
                )}
              >
                {isAvailable ? 'Available' : 'Not Available'}
              </span>
            </div>
            <p className="mt-1 text-ink-600">by {book.author}</p>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {book.genre ? (
                <Link
                  to={`${ROUTES.catalog}?genre=${encodeURIComponent(book.genre)}`}
                  className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 no-underline hover:underline"
                >
                  {book.genre}
                </Link>
              ) : null}
            </div>

            <div className="mt-6">
              {available > 0 && !alreadyBorrowed ? (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setShowBorrowModal(true)}
                >
                  Borrow
                </button>
              ) : (
                <button
                  type="button"
                  className="btn-secondary"
                  disabled
                  aria-describedby="borrow-unavailable-reason"
                >
                  {alreadyBorrowed ? 'Already borrowed' : 'Not Available'}
                </button>
              )}
              <p id="borrow-unavailable-reason" className="mt-2 text-xs text-ink-500">
                {alreadyBorrowed
                  ? 'You already have a copy of this title on loan.'
                  : available > 0
                    ? `${available} of ${total} ${total === 1 ? 'copy is' : 'copies are'} available.`
                    : `Every copy is currently on loan. ${total} ${total === 1 ? 'copy' : 'copies'} in the library.`}
              </p>
            </div>

            <dl className="mt-6 grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-ink-700">ISBN</dt>
                <dd className="text-sm">{book.isbn ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-ink-700">Genre</dt>
                <dd className="text-sm">{book.genre ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-ink-700">Published</dt>
                <dd className="text-sm">{book.published_year ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-ink-700">Copies</dt>
                <dd className="text-sm">
                  {total} total / {available} available
                </dd>
              </div>
            </dl>
          </div>
        </div>

        {book.description ? (
          <section className="mt-6 border-t border-ink-200 pt-6">
            <h2 className="text-base">Description</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-700">{book.description}</p>
          </section>
        ) : null}

        <footer className="mt-6 border-t border-ink-200 pt-4 text-xs text-ink-500">
          <p>Added: {formatUtcDateTime(book.created_at)}</p>
          {book.updated_at ? <p className="mt-1">Last updated: {formatUtcDateTime(book.updated_at)}</p> : null}
        </footer>
      </article>

      {related.length > 0 ? (
        <section className="mt-8" aria-labelledby="related-books-heading">
          <h2 id="related-books-heading" className="text-lg">
            {book.genre ? `More in ${book.genre}` : `More by ${book.author}`}
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {related.map((item) => (
              <BookCard key={item.id} book={item} />
            ))}
          </div>
        </section>
      ) : null}

      <div className="mt-6">
        <button type="button" className="btn-secondary" onClick={() => navigate(ROUTES.catalog)}>
          ← Back to catalog
        </button>
      </div>

      <BorrowModal
        book={book}
        isOpen={showBorrowModal}
        onClose={() => {
          setShowBorrowModal(false);
          setBorrowError('');
          setBorrowSuccess('');
        }}
        onBorrow={handleBorrow}
        borrowing={borrowing}
        error={borrowError}
        success={borrowSuccess}
      />
    </main>
  );
}
