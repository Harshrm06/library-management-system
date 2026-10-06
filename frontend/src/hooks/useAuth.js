/**
 * `useAuth` hook: the single entry point components use to read the session.
 */

import { useContext } from 'react';

import { AuthContext } from '../context/AuthContext';

/**
 * Access the authentication context.
 *
 * @returns {{
 *   isAuthenticated: boolean,
 *   user: object | null,
 *   token: string | null,
 *   loading: boolean,
 *   error: string | null,
 *   isAdmin: boolean,
 *   login: (email: string, password: string) => Promise<{ success: boolean, user?: object, error?: string }>,
 *   register: (formData: object) => Promise<{ success: boolean, fieldErrors?: Record<string, string>, error?: string }>,
 *   logout: () => Promise<void>,
 *   getAuthToken: () => Promise<string | null>,
 *   refreshToken: () => Promise<string | null>,
 *   clearSession: () => void,
 *   setError: (error: string | null) => void,
 * }} Auth state and actions.
 * @throws {Error} When used outside an `AuthProvider`.
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export default useAuth;
