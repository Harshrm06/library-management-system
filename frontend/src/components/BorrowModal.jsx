/**
 * Borrow confirmation dialog.
 *
 * Shows the loan period before the reader commits: today as the issue date and
 * {@link BORROW_PERIOD_DAYS} days later as the due date, plus a small month grid
 * so the due day is unambiguous. The modal never performs the borrow itself; it
 * calls `onBorrow()` and renders whatever loading or error state the page gives
 * it, which keeps the API call in one place.
 *
 * Accessibility: `role="dialog"` with `aria-modal`, labelled by its heading,
 * Escape and backdrop clicks close it, focus moves to the dialog on open and
 * returns to the trigger on close, and Tab is trapped inside while it is open.
 *
 * @example
 * <BorrowModal
 *   book={book}
 *   isOpen={showBorrowModal}
 *   onClose={() => setShowBorrowModal(false)}
 *   onBorrow={handleBorrow}
 *   borrowing={borrowing}
 *   error={borrowError}
 * />
 */

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { CircularProgress } from '@mui/material';

import Toast from './Toast';
import { BORROW_PERIOD_DAYS } from '../utils/constants';
import { addDays, formatDateLong } from '../utils/helpers';

/** Weekday initials for the calendar header, Monday first. */
const WEEKDAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

/** Selectors for elements that can hold focus inside the dialog. */
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Build the day cells for one month, padded to whole Monday-first weeks.
 *
 * Padding cells are marked `outside: true` so the grid can render them muted
 * rather than as real days of the target month.
 *
 * @param {Date} month Any date inside the month to draw.
 * @returns {Array<{ day: number, outside: boolean, key: string }>} Up to 42 cells.
 */
function buildMonthGrid(month) {
  const year = month.getFullYear();
  const monthIndex = month.getMonth();
  const firstOfMonth = new Date(year, monthIndex, 1);

  // getDay() is Sunday-based; shift so Monday is 0.
  const leading = (firstOfMonth.getDay() + 6) % 7;
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
  const cells = [];

  for (let index = 0; index < leading; index += 1) {
    cells.push({ day: null, outside: true, key: `pad-${index}` });
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push({ day, outside: false, key: `day-${day}` });
  }
  // Pad to a whole number of weeks so the grid never changes height.
  while (cells.length % 7 !== 0) {
    cells.push({ day: null, outside: true, key: `pad-end-${cells.length}` });
  }
  return cells;
}

/**
 * Render the borrow confirmation dialog.
 *
 * @param {{
 *   book?: { title?: string, author?: string } | null,
 *   isOpen?: boolean,
 *   onClose?: () => void,
 *   onBorrow?: () => void,
 *   borrowing?: boolean,
 *   error?: string,
 *   success?: string,
 * }} props Component props.
 * @returns {JSX.Element | null} The dialog, or null when closed.
 */
export default function BorrowModal({
  book,
  isOpen = false,
  onClose = () => {},
  onBorrow = () => {},
  borrowing = false,
  error = '',
  success = '',
}) {
  const dialogRef = useRef(null);
  const confirmRef = useRef(null);
  const previouslyFocused = useRef(null);

  // Computed once per open so the issue date does not drift while the dialog is
  // on screen, and the period always spans a whole 14 days.
  const { issueDate, dueDate, monthCells } = useMemo(() => {
    const start = new Date();
    const end = addDays(start, BORROW_PERIOD_DAYS);
    return { issueDate: start, dueDate: end, monthCells: buildMonthGrid(end) };
  }, [isOpen]);

  const close = useCallback(() => {
    // A borrow in flight must not be abandoned half way through.
    if (borrowing) return;
    onClose();
  }, [borrowing, onClose]);

  // Move focus into the dialog on open and hand it back to the trigger on close.
  useEffect(() => {
    if (!isOpen) return undefined;
    previouslyFocused.current = document.activeElement;
    confirmRef.current?.focus();

    return () => {
      if (previouslyFocused.current instanceof HTMLElement) {
        previouslyFocused.current.focus();
      }
    };
  }, [isOpen]);

  // Lock background scrolling while the overlay is up.
  useEffect(() => {
    if (!isOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.stopPropagation();
        close();
        return;
      }
      if (event.key !== 'Tab') return;

      // Trap Tab inside the dialog: the overlay hides everything behind it, so
      // focus must not be able to wander off into an inert page.
      const focusable = dialogRef.current?.querySelectorAll(FOCUSABLE);
      if (!focusable || focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, close]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/50 p-4"
      // A click on the backdrop itself closes; clicks inside the panel stop here.
      onClick={close}
      data-testid="borrow-modal-backdrop"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="borrow-modal-title"
        aria-describedby="borrow-modal-description"
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg"
      >
        <h2 id="borrow-modal-title" className="text-xl">
          Confirm Borrow?
        </h2>
        <p id="borrow-modal-description" className="mt-1 text-sm text-ink-600">
          {book?.title ? `"${book.title}"'s ` : 'This '}
          {book?.author ? `by ${book.author}.` : 'loan.'}
        </p>

        <dl className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-ink-50 p-3">
            <dt className="text-xs uppercase tracking-wide text-ink-500">Issue date</dt>
            <dd className="mt-1 text-sm font-medium text-ink-900">
              {formatDateLong(issueDate)}
            </dd>
          </div>
          <div className="rounded-lg bg-brand-50 p-3">
            <dt className="text-xs uppercase tracking-wide text-ink-500">Due date</dt>
            <dd className="mt-1 text-sm font-medium text-brand-800">
              {formatDateLong(dueDate)}
            </dd>
          </div>
        </dl>

        <section className="mt-4" aria-label={`Due ${formatDateLong(dueDate)}`}>
          <p className="text-sm font-medium text-ink-800">
            {dueDate.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}
          </p>
          <div className="mt-2 grid grid-cols-7 gap-1 text-center text-xs">
            {WEEKDAYS.map((weekday) => (
              <span key={weekday} className="py-1 font-medium text-ink-500">
                {weekday}
              </span>
            ))}
            {monthCells.map((cell) => {
              if (cell.outside) {
                return <span key={cell.key} aria-hidden="true" />;
              }
              const isDue = cell.day === dueDate.getDate();
              return (
                <span
                  key={cell.key}
                  aria-current={isDue ? 'date' : undefined}
                  className={
                    isDue
                      ? 'rounded-md bg-brand-600 py-1 font-semibold text-white'
                      : 'py-1 text-ink-600'
                  }
                >
                  {cell.day}
                </span>
              );
            })}
          </div>
          <p className="sr-only">
            Due on {formatDateLong(dueDate)}, {BORROW_PERIOD_DAYS} days from today.
          </p>
        </section>

        <section className="mt-4 rounded-lg border border-ink-200 bg-ink-50 p-3">
          <h3 className="text-xs uppercase tracking-wide text-ink-500">Borrowing terms</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-ink-700">
            <li>Loans run for {BORROW_PERIOD_DAYS} days from the issue date.</li>
            <li>Return the copy to any branch counter on or before the due date.</li>
            <li>Only one copy of a title may be on loan at a time.</li>
          </ul>
        </section>

        <Toast severity="error" message={error} className="mt-4" />
        <Toast severity="success" message={success} className="mt-4" />

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button type="button" className="btn-secondary" onClick={close} disabled={borrowing}>
            Cancel
          </button>
          <button
            ref={confirmRef}
            type="button"
            className="btn-primary"
            onClick={onBorrow}
            disabled={borrowing}
          >
            {borrowing ? (
              <span className="flex items-center gap-2">
                <CircularProgress size={16} color="inherit" aria-hidden="true" />
                Borrowing…
              </span>
            ) : (
              'Confirm'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
