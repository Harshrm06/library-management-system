/**
 * Application header: branding, primary navigation and the account menu.
 *
 * Layout is mobile first - the navigation and the account menu collapse behind a
 * hamburger button below the `md` breakpoint and sit inline above it. Links are
 * role aware: members never see admin-only destinations, and the current page is
 * highlighted through `NavLink`.
 *
 * Sign-out asks for confirmation in place instead of using `window.confirm`, so
 * it is keyboard reachable and styleable. `Escape` closes both menus, and a
 * click outside the account menu closes it as well.
 *
 * @example
 * <Header />   // mounted once, above <Routes />
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@mui/material';

import { useAuth } from '../hooks/useAuth';
import { getInitials } from '../utils/helpers';
import { ROUTES } from '../utils/constants';

/**
 * Primary navigation, in display order.
 *
 * `adminOnly` entries are filtered out for members; `authOnly` entries are
 * hidden entirely for anonymous visitors.
 *
 * @type {ReadonlyArray<{ to: string, label: string, adminOnly?: boolean }>}
 */
const NAV_LINKS = [
  { to: ROUTES.dashboard, label: 'Home' },
  { to: ROUTES.catalog, label: 'Browse Books' },
  { to: ROUTES.borrowingHistory, label: 'My Borrowing History' },
  { to: ROUTES.adminDashboard, label: 'Admin Dashboard', adminOnly: true },
  { to: ROUTES.adminUsers, label: 'Manage Users', adminOnly: true },
  { to: ROUTES.adminBooks, label: 'Manage Books', adminOnly: true },
  { to: ROUTES.adminBorrowingHistory, label: 'Borrowing History', adminOnly: true },
];

/**
 * Classes for a navigation link, highlighting the active route.
 *
 * @param {{ isActive: boolean }} state NavLink render state.
 * @returns {string} Tailwind classes.
 */
function navLinkClass({ isActive }) {
  return isActive
    ? 'rounded-md bg-brand-50 px-3 py-2 text-sm font-medium text-brand-800'
    : 'rounded-md px-3 py-2 text-sm font-medium text-ink-600 hover:bg-ink-100 hover:text-ink-900';
}

/**
 * Render the top navigation bar.
 *
 * @returns {JSX.Element} The header.
 */
export default function Header() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmingLogout, setConfirmingLogout] = useState(false);
  const menuRef = useRef(null);

  const visibleLinks = NAV_LINKS.filter((link) => !link.adminOnly || isAdmin);

  // Any navigation closes the menus, otherwise they stay open over the new page.
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

  /**
   * Sign the user out and return to the login page.
   *
   * @returns {Promise<void>} Resolves once the navigation is scheduled.
   */
  async function handleLogout() {
    await logout();
    navigate(ROUTES.login, { replace: true });
  }

  const displayName =
    [user?.first_name ?? user?.firstName, user?.last_name ?? user?.lastName]
      .filter(Boolean)
      .join(' ') || user?.email || '';

  /**
   * Render one navigation link.
   *
   * @param {{ to: string, label: string }} link Link descriptor.
   * @param {string} [className] Extra classes for the anchor.
   * @returns {JSX.Element} The link.
   */
  function renderNavLink(link, className) {
    return (
      <NavLink
        key={link.to}
        to={link.to}
        className={(state) =>
          className ? `${className} ${navLinkClass(state)}` : navLinkClass(state)
        }
        end={link.to === ROUTES.dashboard}
        
      >
        {link.label}
      </NavLink>
    );
  }

  return (
    <header className="sticky top-0 z-30 border-b border-ink-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link
          to={ROUTES.home}
          className="flex items-center gap-2 text-lg font-semibold text-ink-900 no-underline"
          aria-label="Library Management home"
        >
          <span
            aria-hidden="true"
            className="flex h-8 w-8 items-center justify-center rounded bg-brand-600 text-sm text-white"
          >
            LM
          </span>
          <span className="hidden sm:inline">Library Management</span>
        </Link>

        {isAuthenticated ? (
          <nav aria-label="Main navigation" className="hidden items-center gap-1 md:flex">
            {visibleLinks.map((link) => renderNavLink(link))}
          </nav>
        ) : null}

        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen((current) => !current)}
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                aria-controls="account-menu"
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-ink-700 hover:bg-ink-100"
              >
                <span
                  aria-hidden="true"
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-800"
                >
                  {getInitials(user)}
                </span>
                <span className="hidden max-w-[10rem] truncate sm:inline">{displayName}</span>
              </button>

              {menuOpen ? (
                <div
                  id="account-menu"
                  role="menu"
                  aria-label="Account"
                  className="absolute right-0 mt-2 w-60 rounded-lg border border-ink-200 bg-white p-2 shadow-lg"
                >
                  <div className="border-b border-ink-100 px-3 py-2">
                    <p className="truncate text-sm font-medium text-ink-900">{displayName}</p>
                    <p className="truncate text-xs text-ink-500">{user?.email}</p>
                    <p className="mt-1 text-xs font-medium uppercase tracking-wide text-brand-700">
                      {user?.role}
                    </p>
                  </div>

                  <Link to={ROUTES.profile} role="menuitem" className="menu-item">
                    View profile
                  </Link>
                  <Link to={ROUTES.profile} role="menuitem" className="menu-item" state={{ edit: true }}>
                    Edit profile
                  </Link>

                  {user?.role === 'admin' && (
                    <Link to={ROUTES.adminDashboard} className="text-blue-600 hover:text-blue-800">
                        Admin Dashboard
                    </Link>
                  )}

                  {confirmingLogout ? (
                    <div className="mt-1 border-t border-ink-100 px-3 py-2">
                      <p className="mb-2 text-xs text-ink-600">Sign out of this device?</p>
                      <div className="flex gap-2">
                        <Button size="small" variant="contained" color="error" onClick={handleLogout}>
                          Sign out
                        </Button>
                        <Button
                          size="small"
                          variant="text"
                          onClick={() => setConfirmingLogout(false)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => setConfirmingLogout(true)}
                      className="menu-item w-full text-left text-red-600 hover:bg-red-50"
                    >
                      Log out
                    </button>
                  )}
                </div>
              ) : null}
            </div>
          ) : (
            <>
              <Button size="small" variant="text" onClick={() => navigate(ROUTES.login)}>
                Log in
              </Button>
              <Button size="small" variant="contained" onClick={() => navigate(ROUTES.register)}>
                Register
              </Button>
            </>
          )}

          <button
            type="button"
            onClick={() => setMobileOpen((current) => !current)}
            aria-expanded={mobileOpen}
            aria-controls="mobile-navigation"
            aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
            className="rounded-md p-2 text-ink-700 hover:bg-ink-100 md:hidden"
          >
            <span aria-hidden="true">{mobileOpen ? '✕' : '☰'}</span>
          </button>
        </div>
      </div>

      {mobileOpen && isAuthenticated ? (
        <nav
          id="mobile-navigation"
          aria-label="Main navigation"
          className="border-t border-ink-200 bg-white px-4 py-2 md:hidden"
        >
          <div className="flex flex-col gap-1">
            {visibleLinks.map((link) => renderNavLink(link, 'block'))}
          </div>
        </nav>
      ) : null}
    </header>
  );
}
