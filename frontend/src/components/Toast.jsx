/**
 * Transient notification banner.
 *
 * Built on MUI's `Alert`, which renders its own dismiss icon, so no
 * `@mui/icons-material` package is required.
 */

import { Alert } from '@mui/material';

/**
 * Render a dismissible message.
 *
 * @param {{
 *   message?: string,
 *   severity?: 'success' | 'info' | 'warning' | 'error',
 *   onClose?: () => void,
 *   className?: string,
 * }} props Component props.
 * @returns {JSX.Element | null} The banner, or null when there is no message.
 */
export default function Toast({ message, severity = 'info', onClose, className = '' }) {
  if (!message) return null;

  return (
    <div className={className}>
      <Alert severity={severity} onClose={onClose} variant="outlined">
        {message}
      </Alert>
    </div>
  );
}
