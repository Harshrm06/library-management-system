/**
 * Catalog card for a single book.
 *
 * Implements a cohesive library aesthetic with cover art placeholders,
 * stock badges, and direct Borrow action support for Members.
 */

import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

import { cx, truncate } from '../utils/helpers';
import { ROUTES } from '../utils/constants';

function titleInitials(book) {
  const words = String(book?.title ?? '')
    .split(/\s+/)
    .filter(Boolean);
  if (words.length === 0) return '?';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
}

// Deterministic subtle book spine tones based on book ID
const SPINE_THEMES = [
  'from-brand-800 to-brand-950 border-brand-700 text-cream-100',
  'from-forest-800 to-forest-950 border-forest-700 text-cream-100',
  'from-amber-800 to-amber-950 border-amber-700 text-cream-100',
  'from-slate-800 to-slate-950 border-slate-700 text-cream-100',
];

export default function BookCard({ book, onBorrow }) {
  const { isAdmin } = useAuth();
  const available = book?.available_quantity ?? 0;
  const total = book?.total_quantity ?? 0;
  const isAvailable = book?.is_available ?? available > 0;
  const detailsPath = `${ROUTES.catalog}/${book.id}`;

  const themeClass = SPINE_THEMES[(book?.id || 0) % SPINE_THEMES.length];

  return (
    <article className="card flex h-full flex-col justify-between hover:shadow-card-hover transition-all duration-200 border-cream-300 bg-white">
      <div>
        {/* Book visual header */}
        <div className="flex items-start gap-3.5">
          {/* Faux Hardcover Book Spine & Cover */}
          <div
            className={`relative flex h-24 w-16 shrink-0 flex-col items-center justify-between rounded-md bg-gradient-to-br p-1.5 shadow-md border ${themeClass}`}
            aria-hidden="true"
          >
            <div className="w-full border-t border-white/20 pt-0.5 text-[8px] font-mono tracking-tighter text-center opacity-70">
              LIB
            </div>
            <div className="font-serif text-sm font-bold tracking-tight text-center leading-tight">
              {titleInitials(book)}
            </div>
            <div className="w-full border-b border-white/20 pb-0.5 text-[7px] font-mono text-center opacity-70 truncate">
              {book?.published_year || 'VOL'}
            </div>
          </div>

          <div className="min-w-0 flex-1">
            <h3 className="font-serif text-base font-bold text-brand-950 leading-snug">
              <Link
                to={detailsPath}
                className="text-brand-950 no-underline hover:text-brand-700 hover:underline"
              >
                {book.title}
              </Link>
            </h3>
            <p className="mt-1 text-xs font-medium text-ink-600">by {book.author}</p>

            <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
              {book.genre ? (
                <span className="rounded-full bg-cream-200 px-2.5 py-0.5 text-[11px] font-semibold text-ink-700">
                  {book.genre}
                </span>
              ) : null}
              <span
                className={cx(
                  'rounded-full px-2.5 py-0.5 text-[11px] font-semibold border',
                  isAvailable
                    ? 'bg-forest-50 text-forest-800 border-forest-300'
                    : 'bg-rose-50 text-rose-800 border-rose-300',
                )}
              >
                {isAvailable ? `${available} Available` : 'Checked Out'}
              </span>
            </div>
          </div>
        </div>

        {/* Metadata Details */}
        <div className="mt-3.5 space-y-1 text-xs text-ink-600 bg-cream-50/70 p-2.5 rounded-lg border border-cream-200">
          <div className="flex justify-between">
            <span className="text-ink-500">ISBN:</span>
            <span className="font-mono text-ink-700">{book.isbn || '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-500">Total Holdings:</span>
            <span className="font-medium text-ink-800">{total} copies</span>
          </div>
        </div>

        {book.description ? (
          <p className="mt-3 text-xs leading-relaxed text-ink-600 line-clamp-2">
            {truncate(book.description, 110)}
          </p>
        ) : null}
      </div>

      {/* Action footer */}
      <div className="mt-4 pt-3 border-t border-cream-200 flex items-center justify-between gap-2">
        <Link
          to={detailsPath}
          className="text-xs font-semibold text-brand-700 no-underline hover:underline"
        >
          View Details →
        </Link>

        {!isAdmin && (
          onBorrow ? (
            <button
              type="button"
              onClick={() => onBorrow(book)}
              disabled={!isAvailable}
              className="rounded-lg bg-forest-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-forest-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Borrow Book
            </button>
          ) : (
            <Link
              to={detailsPath}
              className="rounded-lg bg-brand-50 border border-brand-200 px-3 py-1.5 text-xs font-semibold text-brand-800 hover:bg-brand-100 transition-colors"
            >
              Borrow
            </Link>
          )
        )}
      </div>
    </article>
  );
}
