// Direct browser→Lambda fallback execution (server out of the execution leg).
//
// When Pyodide can't run and VITE_EXERCISE_LAMBDA_URL is set, the hooks call
// the exercise-fallback Lambda's Function URL directly: the API only mints a
// short-lived execution token (/auth/execution-token, dedicated secret — see
// backend/fallback_lambda/exec_token.py) and later receives the result/beacon.
// Any failure here returns { ok: false } so callers fall back to the
// pre-existing server-proxied route — never a dead end.
import { authFetch } from './authFetch';

let cachedToken = null; // { token, expiresAt (ms epoch) }

export function isLambdaDirectEnabled() {
  return Boolean(import.meta.env.VITE_EXERCISE_LAMBDA_URL);
}

async function fetchExecToken(apiUrl, accessToken) {
  if (cachedToken && Date.now() < cachedToken.expiresAt) {
    return cachedToken.token;
  }
  try {
    const response = await authFetch(`${apiUrl}/auth/execution-token`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok) {
      return null;
    }
    const data = await response.json();
    // Tokens are deliberately tiny (10s): reuse only within a 2s safety
    // margin of expiry — back-to-back runs share one token, anything later
    // fetches fresh. A non-positive margin disables caching entirely.
    const cacheMs = (data.expires_in - 2) * 1000;
    if (cacheMs > 0) {
      cachedToken = { token: data.token, expiresAt: Date.now() + cacheMs };
    } else {
      cachedToken = null;
    }
    return data.token;
  } catch (error) {
    console.error('Error fetching execution token:', error);
    return null;
  }
}

/**
 * Run a fallback payload ({ kind: 'exercise'|'snippet', ... }) on the Lambda.
 * Resolves { ok: true, envelope } or { ok: false } — never throws. Uses raw
 * fetch for the Lambda call: its 401 means a stale exec token (cleared and
 * refetched once), not an expired session, so authFetch must not see it.
 */
export async function runOnLambdaDirect(payload, { apiUrl, accessToken }) {
  const lambdaUrl = import.meta.env.VITE_EXERCISE_LAMBDA_URL;
  if (!lambdaUrl) {
    return { ok: false };
  }
  try {
    for (let attempt = 0; attempt < 2; attempt += 1) {
      const execToken = await fetchExecToken(apiUrl, accessToken);
      if (!execToken) {
        return { ok: false };
      }
      const response = await fetch(lambdaUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${execToken}`,
        },
        body: JSON.stringify(payload),
      });
      if (response.status === 401) {
        cachedToken = null;
        continue;
      }
      if (!response.ok) {
        return { ok: false };
      }
      return { ok: true, envelope: await response.json() };
    }
    return { ok: false };
  } catch (error) {
    console.error('Error calling fallback Lambda directly:', error);
    return { ok: false };
  }
}
