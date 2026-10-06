/**
 * Global authentication state.
 *
 * Owns the session (token + user), persists it to `localStorage`, and exposes
 * the actions the pages use. The provider is intentionally router-agnostic: it
 * never navigates, so pages stay in control of redirects.
 *
 * Shape:
 *   { isAuthenticated, user, token, loading, error, isAdmin,
 *     login, register, logout, getAuthToken, refreshToken, clearSession,
 *     setError }
 *
 * @example
 * const { login, user } = useAuth();
 * await login('member@example.com', 'secretpass1');
 */

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import * as authService from '../services/authService';
import { clearStoredSession, setAuthToken } from '../services/api';
import { isTokenExpired } from '../utils/helpers';
import { validateRegistration } from '../utils/validators';
import { ROLES, STORAGE_KEYS } from '../utils/constants';

export const AuthContext = createContext(null);

/** Milliseconds a transient error message stays on screen. */
export const ERROR_TIMEOUT_MS = 5000;

/**
 * Read a value from either storage area.
 *
 * Each area is read independently: browsers throw when storage is blocked, and
 * a broken `sessionStorage` must not stop `localStorage` from being read.
 *
 * @param {string} key Storage key.
 * @returns {string | null} The stored value, or null when absent or blocked.
 */
function readStorage(key) {
  try {
    const persistent = window.localStorage?.getItem(key);
    if (persistent !== null && persistent !== undefined) return persistent;
  } catch {
    /* storage disabled: fall through to sessionStorage */
  }
  try {
    return window.sessionStorage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

/**
 * Write a value, choosing the storage area.
 *
 * @param {string} key Storage key.
 * @param {string | null} value Value to store, or null to remove the key.
 * @param {boolean} [persist] False stores the value in `sessionStorage`, so it
 *   is dropped when the tab closes ("remember me" unchecked).
 */
function writeStorage(key, value, persist = true) {
  const target = persist ? window.localStorage : window.sessionStorage;
  const other = persist ? window.sessionStorage : window.localStorage;
  for (const [storage, item] of [
    [other, null],
    [target, value],
  ]) {
    try {
      if (!storage) continue;
      if (item === null) {
        storage.removeItem(key);
      } else {
        storage.setItem(key, item);
      }
    } catch {
      /* storage disabled (private mode): the in-memory session still works */
    }
  }
}

/**
 * Read the persisted user profile.
 *
 * @returns {object | null} The stored user, or null when absent or corrupt.
 */
function readStoredUser() {
  const raw = readStorage(STORAGE_KEYS.user);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Report whether the current session is stored persistently.
 *
 * A refresh must not silently promote a `sessionStorage` token to
 * `localStorage`, which would make "remember me" meaningless.
 *
 * @returns {boolean} True when the token lives in `localStorage`.
 */
function tokenIsPersistent() {
  try {
    return Boolean(window.localStorage?.getItem(STORAGE_KEYS.token));
  } catch {
    return true;
  }
}

/**
 * Provide authentication state and actions to the tree.
 *
 * @param {{ children: React.ReactNode }} props Component props.
 * @returns {JSX.Element} The provider.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => readStorage(STORAGE_KEYS.token));
  const [loading, setLoading] = useState(true);
  const [error, setErrorState] = useState(null);
  const errorTimer = useRef(null);

  /** Clear the pending error timer, if any. */
  const clearErrorTimer = useCallback(() => {
    if (errorTimer.current) {
      window.clearTimeout(errorTimer.current);
      errorTimer.current = null;
    }
  }, []);

  /**
   * Set (and auto-clear) an error message.
   *
   * @param {string | null} nextError Message to show; null clears it at once.
   */
  const setError = useCallback(
    (nextError) => {
      clearErrorTimer();
      setErrorState(nextError ?? null);
      if (nextError) {
        errorTimer.current = window.setTimeout(() => {
          setErrorState(null);
          errorTimer.current = null;
        }, ERROR_TIMEOUT_MS);
      }
    },
    [clearErrorTimer],
  );

  /** Drop every trace of the session from memory and storage. */
  const clearSession = useCallback(() => {
    setToken(null);
    setUser(null);
    clearStoredSession();
  }, []);

  /**
   * Exchange credentials for a token and load the profile.
   *
   * @param {string} email Registered email address.
   * @param {string} password Account password.
   * @param {{ remember?: boolean }} [options] `remember: false` keeps the token
   *   in `sessionStorage`, so closing the tab signs the user out.
   * @returns {Promise<{ success: boolean, user?: object, error?: string }>}
   *   Result of the attempt; never rejects.
   */
  const login = useCallback(
    async (email, password, { remember = true } = {}) => {
      setLoading(true);
      setError(null);
      const result = await authService.login(email, password);
      if (!result.success) {
        setLoading(false);
        setError(result.message);
        return { success: false, error: result.message };
      }

      const { token: newToken, user: profile } = result.data;
      setAuthToken(newToken, { persist: remember });
      setToken(newToken);
      setUser(profile);
      writeStorage(STORAGE_KEYS.user, JSON.stringify(profile), remember);
      writeStorage(STORAGE_KEYS.rememberMe, remember ? 'true' : 'false', true);
      setLoading(false);
      return { success: true, user: profile };
    },
    [setError],
  );

  /**
   * Create an account. The backend does not return a token for a new member,
   * so the caller redirects to the login page afterwards.
   *
   * @param {{ firstName: string, lastName: string, email: string, password: string, phone?: string, address?: string }} formData
   *   Registration values.
   * @returns {Promise<{ success: boolean, fieldErrors?: Record<string, string>, error?: string }>}
   *   Result of the attempt; never rejects.
   */
  const register = useCallback(
    async (formData) => {
      setLoading(true);
      setError(null);

      const fieldErrors = validateRegistration(formData);
      if (Object.keys(fieldErrors).length > 0) {
        setLoading(false);
        return { success: false, fieldErrors };
      }

      const result = await authService.register(formData);
      setLoading(false);

      if (result.success) {
        return { success: true };
      }
      // A duplicate email is a field-level problem, not a banner-level one.
      if (result.error?.code === 'email_taken') {
        return {
          success: false,
          fieldErrors: { email: 'That email is already registered' },
        };
      }
      if (Object.keys(result.error?.fieldErrors ?? {}).length > 0) {
        return { success: false, fieldErrors: result.error.fieldErrors };
      }
      setError(result.message);
      return { success: false, error: result.message };
    },
    [setError],
  );

  /**
   * Sign the user out locally and, best effort, on the server.
   *
   * @returns {Promise<void>} Resolves once the session is cleared.
   */
  const logout = useCallback(async () => {
    await authService.logout();
    clearSession();
  }, [clearSession]);

  /**
   * Mint a new access token for the current session.
   *
   * @returns {Promise<string | null>} The new token, or null when the session
   *   cannot be refreshed.
   */
  const refreshToken = useCallback(async () => {
    const result = await authService.refreshToken();
    if (!result.success) {
      clearSession();
      return null;
    }
    setAuthToken(result.data.token, { persist: tokenIsPersistent() });
    setToken(result.data.token);
    return result.data.token;
  }, [clearSession]);

  /**
   * Return a usable token, refreshing it first when it has expired.
   *
   * @returns {Promise<string | null>} A valid token, or null when signed out.
   */
  const getAuthToken = useCallback(async () => {
    const current = token ?? readStorage(STORAGE_KEYS.token);
    if (!current) return null;
    if (!isTokenExpired(current)) {
      setAuthToken(current, { persist: tokenIsPersistent() });
      return current;
    }
    return refreshToken();
  }, [refreshToken, token]);

  // Restore the session on mount and validate the stored token.
  useEffect(() => {
    let cancelled = false;

    async function initialise() {
      const storedToken = readStorage(STORAGE_KEYS.token);
      const storedUser = readStoredUser();
      const persist = tokenIsPersistent();

      if (!storedToken) {
        if (!cancelled) setLoading(false);
        return;
      }

      setToken(storedToken);
      setAuthToken(storedToken, { persist });

      // Hydrate optimistically so the header renders immediately; the
      // request below replaces it with the verified profile.
      if (storedUser) {
        setUser(storedUser);
      }

      if (isTokenExpired(storedToken)) {
        clearSession();
        if (!cancelled) setLoading(false);
        return;
      }

      try {
        const result = await authService.getCurrentUser();
        if (cancelled) return;
        if (result.success) {
          setUser(result.data.user);
          writeStorage(STORAGE_KEYS.user, JSON.stringify(result.data.user), persist);
        } else {
          clearSession();
          setError(result.message);
        }
      } catch (initError) {
        if (!cancelled) {
          clearSession();
          setError(initError?.message || 'Session could not be restored');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    initialise();
    return () => {
      cancelled = true;
    };
  }, [clearSession, setError]);

  useEffect(() => clearErrorTimer, [clearErrorTimer]);

  const value = useMemo(
    () => ({
      isAuthenticated: Boolean(user),
      user,
      token,
      loading,
      error,
      isAdmin: user?.role === ROLES.admin,
      login,
      register,
      logout,
      getAuthToken,
      refreshToken,
      clearSession,
      setError,
    }),
    [user, token, loading, error, login, register, logout, getAuthToken, refreshToken, clearSession, setError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthContext;
