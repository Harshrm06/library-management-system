/**
 * Application header: branding, primary navigation and the account menu.
 *
 * Implements a cohesive, premium library aesthetic with deep navy accents,
 * role-aware navigation, and strict removal of public member self-registration.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import { getInitials } from '../utils/helpers';
import { ROUTES } from '../utils/constants';

/**
 * Primary navigation items, role-configured.
 */
const MEMBER_NAV_LINKS = [
  { to: ROUTES.dashboard, label: 'Dashboard' },
  { to: ROUTES.catalog, label: 'Catalog' },
  { to: ROUTES.borrowingHistory, label: 'My Loans' },
];

const ADMIN_NAV_LINKS = [
  { to: ROUTES.adminDashboard, label: 'Admin Hub' },
  { to: ROUTES.catalog, label: 'Catalog' },
  { to: ROUTES.adminBooks, label: 'Manage Books' },
  { to: ROUTES.adminUsers, label: 'Manage Members' },
  { to: ROUTES.adminBorrowingHistory, label: 'Circulation' },
  { to: ROUTES.borrowingHistory, label: 'My Loans' },
];

function navLinkClass({ isActive }) {
  return isActive
    ? 'rounded-lg bg-brand-50 text-brand-800 font-semibold px-3 py-2 text-sm border border-brand-200 transition-all'
    : 'rounded-lg px-3 py-2 text-sm font-medium text-ink-600 hover:bg-cream-200 hover:text-ink-900 transition-all';
}

export default function Header() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmingLogout, setConfirmingLogout] = useState(false);
  const menuRef = useRef(null);

  const visibleLinks = isAdmin ? ADMIN_NAV_LINKS : MEMBER_NAV_LINKS;

  useEffect(() => {
    setMobileOpen(false);
    setMenuOpen(false);
    setConfirmingLogout(false);
  }, [location.pathname]);

  const closeOnOutsideClick = useCallback((event) => {
    if (menuRef.current && !menuRef.current.contains(event.target)) {
      setMenuOpen(false);
      setConfirmingLogout(false);
    }
  }, []);

  useEffect(() => {
    if (!menuOpen) return undefined;
    document.addEventListener('mousedown', closeOnOutsideClick);
    return () => document.removeEventListener('mousedown', closeOnOutsideClick);
  }, [menuOpen, closeOnOutsideClick]);

  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key !== 'Escape') return;
      setMenuOpen(false);
      setMobileOpen(false);
      setConfirmingLogout(false);
    }
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, []);

  async function handleLogout() {
    await logout();
    navigate(ROUTES.login, { replace: true });
  }

  const displayName =
    [user?.first_name ?? user?.firstName, user?.last_name ?? user?.lastName]
      .filter(Boolean)
      .join(' ') || user?.email || 'Member';

  return (
    <header className="sticky top-0 z-30 border-b border-cream-300 bg-white/95 backdrop-blur-md shadow-sm">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link
          to={isAuthenticated ? (isAdmin ? ROUTES.adminDashboard : ROUTES.dashboard) : ROUTES.login}
          className="flex items-center gap-2.5 text-lg font-bold text-brand-900 no-underline tracking-tight"
          aria-label="Athenaeum Library Management"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-700 text-white shadow-sm ring-1 ring-brand-800">
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
              <path d="M6 6h10" />
              <path d="M6 10h10" />
              <path d="M6 14h6" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-base font-bold tracking-tight text-brand-900 leading-tight">
              Athenaeum
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-forest-700 leading-none">
              Library System
            </span>
          </div>
        </Link>

        {/* Navigation - Authenticated */}
        {isAuthenticated ? (
          <nav aria-label="Main navigation" className="hidden items-center gap-1 lg:flex">
            {visibleLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={navLinkClass}
                end={link.to === ROUTES.dashboard || link.to === ROUTES.adminDashboard}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        ) : null}

        {/* Account controls */}
        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen((current) => !current)}
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                aria-controls="account-menu"
                className="flex items-center gap-2.5 rounded-lg border border-cream-300 bg-cream-50 px-2.5 py-1.5 text-sm text-ink-800 hover:bg-cream-100 transition-colors"
              >
                <span
                  aria-hidden="true"
                  className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-700 text-xs font-semibold text-white shadow-inner"
                >
                  {getInitials(user)}
                </span>
                <span className="hidden max-w-[9rem] truncate font-medium text-xs sm:inline">
                  {displayName}
                </span>
                <span
                  className={`hidden sm:inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                    isAdmin
                      ? 'bg-amber-100 text-amber-800 border border-amber-300'
                      : 'bg-forest-100 text-forest-800 border border-forest-300'
                  }`}
                >
                  {user?.role}
                </span>
                <svg
                  className={`h-4 w-4 text-ink-400 transition-transform ${menuOpen ? 'rotate-180' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {menuOpen && (
                <div
                  id="account-menu"
                  role="menu"
                  aria-label="Account"
                  className="absolute right-0 mt-2 w-64 rounded-xl border border-cream-300 bg-white p-2 shadow-elevation z-50 animate-in fade-in slide-in-from-top-1"
                >
                  <div className="border-b border-cream-200 px-3 py-2.5 mb-1 bg-cream-50 rounded-lg">
                    <p className="truncate text-sm font-semibold text-ink-900">{displayName}</p>
                    <p className="truncate text-xs text-ink-500">{user?.email}</p>
                    <div className="mt-1.5 flex items-center gap-1.5">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          isAdmin
                            ? 'bg-amber-100 text-amber-800 border border-amber-300'
                            : 'bg-forest-100 text-forest-800 border border-forest-300'
                        }`}
                      >
                        {user?.role}
                      </span>
                    </div>
                  </div>

                  <Link
                    to={ROUTES.profile}
                    role="menuitem"
                    className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink-700 hover:bg-cream-100 transition-colors"
                  >
                    <span>User Profile</span>
                  </Link>

                  {isAdmin && (
                    <Link
                      to={ROUTES.adminDashboard}
                      role="menuitem"
                      className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50 transition-colors"
                    >
                      <span>Admin Overview</span>
                    </Link>
                  )}

                  <div className="my-1 border-t border-cream-200" />

                  {confirmingLogout ? (
                    <div className="p-2 bg-rose-50 rounded-lg border border-rose-200">
                      <p className="text-xs text-rose-800 font-medium mb-2">Sign out of your session?</p>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={handleLogout}
                          className="flex-1 rounded-md bg-rose-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-rose-700"
                        >
                          Sign out
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmingLogout(false)}
                          className="flex-1 rounded-md border border-ink-300 bg-white px-2.5 py-1 text-xs font-medium text-ink-700 hover:bg-ink-100"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => setConfirmingLogout(true)}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-rose-600 hover:bg-rose-50 transition-colors"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                        />
                      </svg>
                      <span>Sign out</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <Link
              to={ROUTES.login}
              className="btn-primary"
            >
              Sign in
            </Link>
          )}

          {/* Mobile hamburger button */}
          {isAuthenticated && (
            <button
              type="button"
              onClick={() => setMobileOpen((current) => !current)}
              aria-expanded={mobileOpen}
              aria-controls="mobile-navigation"
              aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
              className="rounded-lg border border-cream-300 p-2 text-ink-700 hover:bg-cream-100 lg:hidden"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {mobileOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && isAuthenticated ? (
        <nav
          id="mobile-navigation"
          aria-label="Main navigation"
          className="border-t border-cream-300 bg-white px-4 py-3 lg:hidden"
        >
          <div className="flex flex-col gap-1.5">
            {visibleLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={navLinkClass}
                end={link.to === ROUTES.dashboard || link.to === ROUTES.adminDashboard}
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        </nav>
      ) : null}
    </header>
  );
}
