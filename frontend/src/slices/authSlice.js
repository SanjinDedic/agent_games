import { createSlice } from '@reduxjs/toolkit';
import moment from 'moment-timezone';
import { clearLeagues } from './leaguesSlice';
import { clearTeam } from './teamsSlice';

moment.tz.setDefault("Australia/Sydney");

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    token: null,
    currentUser: {
      name: null,
      role: null,
      exp: null,
      is_demo: false,  // Add this field
    },
    isAuthenticated: false,
  },
  reducers: {
    setCredentials: (state, action) => {
      const { token, user } = action.payload;
      state.token = token;
      state.currentUser = user;
      state.isAuthenticated = true;
    },
    login: (state, action) => {
      const { token, name, role, exp, is_demo } = action.payload;  // Extract is_demo
      state.token = token;
      state.currentUser = { name, role, exp, is_demo: is_demo || false };  // Include is_demo
      state.isAuthenticated = true;
    },
    logout: (state) => {
      state.token = null;
      state.currentUser = { name: null, role: null, exp: null };
      state.isAuthenticated = false;
    },
  },
});

export const checkTokenExpiry = () => (dispatch, getState) => {
  const { currentUser } = getState().auth;

  if (currentUser.exp) {
    const expiryDate = moment.unix(currentUser.exp);
    const currentDate = moment();

    if (currentDate.isAfter(expiryDate)) {
      dispatch(authSlice.actions.logout());
      dispatch(clearLeagues());
      dispatch(clearTeam());
      return true;
    }
  }
  return false;
};

export const { setCredentials, login, logout } = authSlice.actions;
export default authSlice.reducer;