import { createSlice, createSelector } from '@reduxjs/toolkit';
import { jwtDecode } from 'jwt-decode';
import moment from 'moment-timezone';
import { clearLeagues } from './leaguesSlice';
import { clearTeam } from './teamsSlice';

moment.tz.setDefault("Australia/Sydney");

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    token: null,
  },
  reducers: {
    setToken: (state, action) => {
      state.token = action.payload;
    },
    clearToken: (state) => {
      state.token = null;
    },
  },
});

export const { setToken, clearToken } = authSlice.actions;

// Backwards-compatible action creators. Login accepts either a raw token
// string or the legacy `{ token, ... }` payload (extra fields are ignored —
// everything is derived from the JWT now).
export const login = (payload) => {
  const token = typeof payload === 'string' ? payload : payload?.token;
  return setToken(token);
};
export const setCredentials = ({ token }) => setToken(token);
export const logout = clearToken;

// --- Selectors ---------------------------------------------------------

export const selectToken = (state) => state.auth.token;

export const selectDecodedToken = createSelector(
  [selectToken],
  (token) => {
    if (!token) return null;
    try {
      return jwtDecode(token);
    } catch {
      return null;
    }
  }
);

export const selectCurrentUser = createSelector(
  [selectDecodedToken],
  (decoded) => {
    if (!decoded) {
      return { name: null, role: null, exp: null, is_demo: false };
    }
    return {
      name: decoded.sub ?? null,
      role: decoded.role ?? null,
      exp: decoded.exp ?? null,
      is_demo: decoded.is_demo ?? false,
      team_id: decoded.team_id ?? null,
      team_type: decoded.team_type ?? null,
      league_id: decoded.league_id ?? null,
      institution_id: decoded.institution_id ?? null,
      institution_name: decoded.institution_name ?? null,
    };
  }
);

export const selectIsAuthenticated = createSelector(
  [selectDecodedToken],
  (decoded) => {
    if (!decoded || !decoded.exp) return false;
    return moment().unix() < decoded.exp;
  }
);

export const selectRole = (state) => selectCurrentUser(state).role;
export const selectTeamId = (state) => selectCurrentUser(state).team_id;
export const selectTeamName = (state) => selectCurrentUser(state).name;
export const selectInstitutionId = (state) => selectCurrentUser(state).institution_id;
export const selectInstitutionName = (state) => selectCurrentUser(state).institution_name;
export const selectLeagueId = (state) => selectCurrentUser(state).league_id;
export const selectIsDemo = (state) => selectCurrentUser(state).is_demo;
export const selectTokenExp = (state) => selectCurrentUser(state).exp;

// --- Token expiry thunk ------------------------------------------------

export const checkTokenExpiry = () => (dispatch, getState) => {
  const exp = selectTokenExp(getState());
  if (!exp) return false;

  const expiryDate = moment.unix(exp);
  if (moment().isAfter(expiryDate)) {
    dispatch(clearToken());
    dispatch(clearLeagues());
    dispatch(clearTeam());
    return true;
  }
  return false;
};

export default authSlice.reducer;
