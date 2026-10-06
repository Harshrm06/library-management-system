/**
 * Connects the HTTP layer to the router.
 *
 * `services/api.js` owns the policy for 401 / 403 / 404 / 500 responses but
 * cannot import React or the router. This component registers the handler that
 * turns those events into navigation and a visible message, and is mounted
 * inside `BrowserRouter` so `useNavigate` is available.
 *
 * Events handled:
 * * **401** - the interceptor has already dropped the stored session; React
 *   state is cleared here and the user is sent to the login page with
 *   `sessionExpired` set, so the form can explain why they are back there.
 * * **403 / 404 / 500** - shown through the auth context's `error` state, which
 *   the header renders as a toast.
 *
 * @example
 * <BrowserRouter>
 *   <AuthProvider>
 *     <ApiEventBridge />
 *     <App />
 *   </AuthProvider>
 * </BrowserRouter>
 */

import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import { registerApiEventHandler } from '../services/api';
import { ROUTES } from '../utils/constants';

/**
 * Register the API event handler for the lifetime of the app.
 *
 * @returns {null} Renders nothing.
 */
export default function ApiEventBridge() {
  const { clearSession, setError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    registerApiEventHandler({
      onUnauthorized: () => {
        clearSession();
        if (location.pathname !== ROUTES.login) {
          navigate(ROUTES.login, { replace: true, state: { sessionExpired: true } });
        }
      },
      onError: ({ message }) => setError(message),
    });

    return () => registerApiEventHandler(null);
  }, [clearSession, setError, navigate, location.pathname]);

  return null;
}