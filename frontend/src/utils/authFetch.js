let _onUnauthorized = () => {};

// Wired at boot in store.js so this module stays free of any Redux imports.
export function registerOnUnauthorized(handler) {
  _onUnauthorized = handler;
}

/**
 * Drop-in replacement for fetch() that signals expired sessions.
 * On a 401 response, invokes the registered handler (which dispatches
 * `sessionExpired` and triggers logout + redirect via the auth-error
 * middleware) and returns a JSON 401 response so callers can still safely
 * .json() on it.
 * Usage: authFetch(url, options) — same signature as window.fetch.
 */
export async function authFetch(url, options = {}) {
  const response = await fetch(url, options);

  if (response.status === 401) {
    _onUnauthorized();
    return new Response(
      JSON.stringify({ status: 'error', message: 'Session expired' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } },
    );
  }

  return response;
}
