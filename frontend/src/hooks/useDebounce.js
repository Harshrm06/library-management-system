/**
 * `useDebounce` - delay a fast-changing value.
 *
 * Search inputs update on every keystroke; sending each one to the API would
 * fire a request per character. This hook returns the previous value until the
 * input has been quiet for `delay` milliseconds, so the page re-renders freely
 * while only settled terms reach the service layer.
 *
 * @example
 * const [term, setTerm] = useState('');
 * const debouncedTerm = useDebounce(term, 300);
 *
 * useEffect(() => {
 *   fetchBooks(debouncedTerm);
 * }, [debouncedTerm]);
 */

import { useEffect, useState } from 'react';

/** Quiet period, in milliseconds, before a value is published. */
export const DEFAULT_DEBOUNCE_MS = 300;

/**
 * Return `value` after it has stopped changing for `delay` milliseconds.
 *
 * The pending timer is cleared on every change and on unmount, so a page that is
 * navigated away from mid-typing never sets state afterwards.
 *
 * @param {*} value The value to debounce.
 * @param {number} [delay] Quiet period in milliseconds.
 * @returns {*} The value from the end of the last quiet period.
 */
export default function useDebounce(value, delay = DEFAULT_DEBOUNCE_MS) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    // A zero or negative delay means "no debouncing"; publish immediately rather
    // than scheduling a task that could fire after the component unmounts.
    if (delay <= 0) {
      setDebounced(value);
      return undefined;
    }

    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}
