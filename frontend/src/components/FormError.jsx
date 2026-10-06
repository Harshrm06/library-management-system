/**
 * Inline error/validation message for a form field or a form submission.
 */

import { cx } from '../utils/helpers';

/**
 * Render an error message.
 *
 * @param {{ message?: string, id?: string, className?: string }} props
 *   Component props. `id` lets the control point at the message through
 *   `aria-describedby`.
 * @returns {JSX.Element | null} The message, or null when there is nothing to show.
 */
export default function FormError({ message, id, className }) {
  if (!message) return null;

  return (
    <p id={id} className={cx('mt-1 text-sm text-red-600', className)} role="alert">
      {message}
    </p>
  );
}
