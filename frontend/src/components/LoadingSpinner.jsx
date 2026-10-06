/**
 * Full-screen loader used while a page or the session is initialising.
 */

import { CircularProgress } from '@mui/material';

/**
 * Render a centred spinner.
 *
 * @param {{ label?: string, fullScreen?: boolean }} props Component props.
 * @returns {JSX.Element} The spinner.
 */
export default function LoadingSpinner({ label = 'Loading…', fullScreen = false }) {
  const containerClass = fullScreen
    ? 'min-h-screen flex flex-col items-center justify-center gap-3 bg-ink-50'
    : 'flex items-center justify-center gap-3 py-10';

  return (
    <div className={containerClass} role="status" aria-live="polite">
      <CircularProgress size={fullScreen ? 40 : 28} />
      <span className="text-sm text-ink-600">{label}</span>
    </div>
  );
}
