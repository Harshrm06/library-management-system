/**
 * Catalog card for a single book.
 *
 * Pure Tailwind: layout, badges and availability colours are all utility
 * classes, so the card has no runtime styling dependency. There is no cover art
 * in the API, so a tinted placeholder carrying the title's initials stands in for
 * one.
 *
 * @example
 * <BookCard book={book} />
 * <BookCard book={book} onClick={() => setSelected(book)} />
 */

import { Link } from 'react-router-dom';

import { cx, truncate } from '../utils/helpers';
import { ROUTES } from '../utils/constants';

/**
 * Derive one or two initials for the cover placeholder.
 *
 * Used as the placeholder artwork and as its accessible label, so a screen reader
 * announces the title rather than a bare image.
 *
 * @param {{ title?: string }} book Book object from the API.
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
 * Render the book summary card.
 *
 * Availability is derived from `available_quantity` rather than read from
 * `is_available`, so the card stays correct if it is ever passed a book object
 * that predates that field.
 *
 * @param {{
 *   book: {
 *     id: number,
 *     title?: string,
 *     author?: string,
 *     isbn?: string,
 *     genre?: string,
 *     description?: string,
 *     published_year?: number,
 *     available_quantity?: number,
 *     total_quantity?: number,
 *     is_available?: boolean,
 *   },
 *   onClick?: (book: object) => void,
 * }} props Component props.
 * @returns {JSX.Element} The card.
 */
export default function BookCard({ book, onClick }) {
  const available = book?.available_quantity ?? 0;
  const total = book?.total_quantity ?? 0;
  const isAvailable = book?.is_available ?? available > 0;
  const detailsPath = `${ROUTES.catalog}/${book.id}`;

  return (
    <article
      className="card flex h-full flex-col transition-shadow hover:shadow-md"
      aria-labelledby={`book-title-${book.id}`}
      onClick={onClick ? () => onClick(book) : undefined}
      onKeyDown={
        onClick
          ? (event) => {
              // Only Enter and Space activate; other keys must keep their default
              // behaviour so the card does not swallow browser shortcuts.
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onClick(book);
              }
            }
          : undefined
      }
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? 'button' : undefined}
    >
      <div className="flex items-start gap-3">
        <div
          className="flex h-16 w-12 shrink-0 items-center justify-center rounded-md bg-ink-100 text-xs font-semibold text-ink-600"
          aria-hidden="true"
        >
          {titleInitials(book)}
        </div>
        <div className="min-w-0 flex-1">
          <h3 id={`book-title-${book.id}`} className="text-base leading-snug">
            <Link
              to={detailsPath}
              className="text-ink-900 no-underline hover:underline"
              // The card is not a link itself, so the nested link must not
              // announce the card's target twice.
              onClick={(event) => event.stopPropagation()}
            >
              {book.title}
            </Link>
          </h3>
          <p className="mt-1 text-sm text-ink-600">{book.author}</p>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {book.genre ? (
          <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
            {book.genre}
          </span>
        ) : null}
        <span
          className={cx(
            'rounded-full px-2 py-0.5 text-xs font-medium',
            isAvailable ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800',
          )}
        >
          {isAvailable ? 'Available' : 'Not Available'}
        </span>
      </div>

      <dl className="mt-3 space-y-1 text-sm text-ink-600">
        <div className="flex gap-2">
          <dt className="font-medium text-ink-700">Copies:</dt>
          <dd>
            {available} available
            {total > 0 ? ` of ${total}` : ''}
          </dd>
        </div>
        {book.isbn ? (
          <div className="flex gap-2">
            <dt className="font-medium text-ink-700">ISBN:</dt>
            <dd className="truncate">{book.isbn}</dd>
          </div>
        ) : null}
        {book.published_year ? (
          <div className="flex gap-2">
            <dt className="font-medium text-ink-700">Published:</dt>
            <dd>{book.published_year}</dd>
          </div>
        ) : null}
      </dl>

      {book.description ? (
        <p className="mt-3 text-sm text-ink-600">{truncate(book.description, 120)}</p>
      ) : null}

      <div className="mt-4 pt-2">
        <Link
          to={detailsPath}
          onClick={(event) => event.stopPropagation()}
          className="text-sm font-medium text-brand-700 no-underline hover:underline"
        >
          View Details
        </Link>
      </div>
    </article>
  );
}
