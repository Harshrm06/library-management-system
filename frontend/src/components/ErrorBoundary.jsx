/**
 * Top-level error boundary.
 *
 * React only supports error boundaries as class components, so this file is
 * the one place in `src/` that is not a function component.
 */

import { Component } from 'react';

import Toast from './Toast';

/**
 * Catch render errors and show a recovery screen.
 */
export default class ErrorBoundary extends Component {
  /**
   * @param {object} props Component props.
   */
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  /**
   * Derive error state from the props that caused the render failure.
   *
   * @param {Error} error The thrown error.
   * @returns {{ hasError: boolean, message: string }} New state.
   */
  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      message: error?.message || 'Unexpected application error',
    };
  }

  /**
   * Log the error for developers.
   *
   * @param {Error} error The thrown error.
   * @param {object} info React component stack.
   */
  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('Unhandled UI error:', error, info?.componentStack);
  }

  /**
   * Clear the error state and re-render the subtree.
   */
  handleReset = () => {
    this.setState({ hasError: false, message: '' });
  };

  /**
   * @returns {JSX.Element} Either the children or the error screen.
   */
  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <main className="page-container">
        <h1 className="mb-2 text-2xl">Something went wrong</h1>
        <Toast severity="error" message={this.state.message} className="mb-4" />
        <button type="button" className="btn-secondary" onClick={this.handleReset}>
          Try again
        </button>
      </main>
    );
  }
}
