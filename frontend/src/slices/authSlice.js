import { createSlice } from '@reduxjs/toolkit';

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    token: null,
    currentUser: {
      name: null,
      role: null,
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
      const { token, name, role } = action.payload;
      state.token = token;
      state.currentUser = { name, role };
      state.isAuthenticated = true;
    },
    logout: (state) => {
      state.token = null;
      state.currentUser = { name: null, role: null };
      state.isAuthenticated = false;
    },
  },
});

export const { setCredentials, login, logout } = authSlice.actions;
export default authSlice.reducer;