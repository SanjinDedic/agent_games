import React from 'react';

/**
 * Last-resort catch for render crashes. Without this, one component throwing
 * during render unmounts the entire app and leaves a blank white page with no
 * way out. "Reset and reload" also clears the persisted Redux state, since a
 * stale/corrupt session blob is the most likely cause of a render crash.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('Unhandled render error:', error, info.componentStack);
  }

  handleReset = () => {
    try {
      sessionStorage.removeItem('reduxState');
    } catch {
      // storage unavailable — reload alone still gives a fresh tree
    }
    window.location.href = '/';
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="min-h-screen flex items-center justify-center bg-ui-lighter px-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <h1 className="text-2xl font-bold text-ui-dark mb-2">
            Something went wrong
          </h1>
          <p className="text-ui-dark/70 mb-6">
            The page hit an unexpected error. Resetting your session usually
            fixes this — you may need to log in again.
          </p>
          <button
            onClick={this.handleReset}
            className="py-3 px-6 text-lg font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200"
          >
            Reset and reload
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
