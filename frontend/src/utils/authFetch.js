import { store } from "../store";
import { logout } from "../slices/authSlice";
import { clearLeagues } from "../slices/leaguesSlice";
import { clearTeam } from "../slices/teamsSlice";

const LOGIN_ROUTES = {
  admin: "/Admin",
  institution: "/Institution",
  student: "/AgentLogin",
};

let isLoggingOut = false;

function handleSessionExpired() {
  if (isLoggingOut) return;
  isLoggingOut = true;

  const { auth } = store.getState();
  const role = auth.currentUser?.role;
  const isDemo = auth.currentUser?.is_demo;

  store.dispatch(logout());
  store.dispatch(clearLeagues());
  store.dispatch(clearTeam());

  const redirectTo = isDemo ? "/" : (LOGIN_ROUTES[role] || "/");
  window.location.href = redirectTo;

  // Reset flag after redirect starts
  setTimeout(() => {
    isLoggingOut = false;
  }, 1000);
}

/**
 * Drop-in replacement for fetch() that handles expired sessions.
 * On a 401 response, it logs the user out and redirects to their login page.
 * Usage: authFetch(url, options) — same signature as window.fetch.
 */
export async function authFetch(url, options = {}) {
  const response = await fetch(url, options);

  if (response.status === 401) {
    handleSessionExpired();
    // Return a response that callers can still safely .json() on
    return new Response(JSON.stringify({ status: "error", message: "Session expired" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  return response;
}
