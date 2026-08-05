// Direct browser→Lambda fallback execution (the server never runs the code).
//
// When Pyodide can't run on a student/team page, the hooks call the matching
// Lambda's Function URL directly — exercises/snippets go to the exercise
// fallback (VITE_EXERCISE_LAMBDA_URL), agent validation to the validation
// Lambda (VITE_VALIDATION_LAMBDA_URL), selected by payload.kind. The API only
// mints a short-lived execution token (/auth/execution-token, dedicated
// secret — see the Lambdas' exec_token.py) and later receives the
// result/beacon. This is the ONLY fallback path — { ok: false } means the
// caller shows an error, there is no server-proxied retry.
// Admin/institution preview surfaces never call this: they are Pyodide-only.
import { authFetch } from './authFetch';

// Keyed by the session token so a logout/login as someone else can never
// reuse the previous user's exec token, without any coupling to authSlice.
let cachedToken = null; // { token, expiresAt (ms epoch), forAccessToken }

const TOKEN_FETCH_TIMEOUT_MS = 8000;

const LAMBDA_URLS = {
  exercise: import.meta.env.VITE_EXERCISE_LAMBDA_URL,
  snippet: import.meta.env.VITE_EXERCISE_LAMBDA_URL,
  validation: import.meta.env.VITE_VALIDATION_LAMBDA_URL,
};

// Per-kind budgets: the exercise Lambda's hard timeout is 3s, the validation
// Lambda's is 8s (6s in-child hard limit); the rest is headroom for a cold
// start plus the VPC ENI attach. A hung Function URL call must never hang
// the submit.
const LAMBDA_FETCH_TIMEOUT_MS = {
  exercise: 15000,
  snippet: 15000,
  validation: 20000,
};

export function isLambdaDirectEnabled(kind = 'exercise') {
  return Boolean(LAMBDA_URLS[kind]);
}

async function fetchExecToken(apiUrl, accessToken) {
  if (
    cachedToken &&
    cachedToken.forAccessToken === accessToken &&
    Date.now() < cachedToken.expiresAt
  ) {
    return cachedToken.token;
  }
  try {
    const response = await authFetch(`${apiUrl}/auth/execution-token`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      signal: AbortSignal.timeout(TOKEN_FETCH_TIMEOUT_MS),
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
      cachedToken = {
        token: data.token,
        expiresAt: Date.now() + cacheMs,
        forAccessToken: accessToken,
      };
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
 * Run a fallback payload ({ kind: 'exercise'|'snippet'|'validation', ... })
 * on that kind's Lambda. Resolves { ok: true, envelope } or { ok: false } —
 * never throws. Uses raw fetch for the Lambda call: its 401 means a stale
 * exec token (cleared and refetched once), not an expired session, so
 * authFetch must not see it.
 */
export async function runOnLambdaDirect(payload, { apiUrl, accessToken }) {
  const lambdaUrl = LAMBDA_URLS[payload.kind];
  if (!lambdaUrl) {
    return { ok: false };
  }
  const fetchTimeoutMs =
    LAMBDA_FETCH_TIMEOUT_MS[payload.kind] ?? LAMBDA_FETCH_TIMEOUT_MS.exercise;
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
        signal: AbortSignal.timeout(fetchTimeoutMs),
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
