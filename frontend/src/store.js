import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import teamsReducer from './slices/teamsSlice';
import leaguesReducer from './slices/leaguesSlice';
import gamesReducer from './slices/gamesSlice.js';
import rankingsReducer from './slices/rankingsSlice';
import settingsReducer from './slices/settingsSlice';
import feedbackReducer from './slices/feedbackSlice';
import supportReducer from './slices/supportSlice';
import {
  authErrorMiddleware,
  sessionExpired,
} from './middleware/authErrorMiddleware';
import { registerOnUnauthorized } from './utils/authFetch';

const saveState = (state) => {
  try {
    // immersiveMode mirrors the live browser-fullscreen state, which never
    // survives a reload — persisting true would hide the navbar with no way back
    const serializedState = JSON.stringify({
      ...state,
      settings: { ...state.settings, immersiveMode: false },
    });
    sessionStorage.setItem('reduxState', serializedState); // Use sessionStorage instead of localStorage
  } catch (e) {
    console.warn('Error saving state to session storage:', e);
  }
};

const loadState = () => {
  try {
    const serializedState = sessionStorage.getItem('reduxState'); // Use sessionStorage instead of localStorage
    if (serializedState === null) {
      return undefined;
    }
    return JSON.parse(serializedState);
  } catch (e) {
    console.warn('Error loading state from session storage:', e);
    return undefined;
  }
};

const persistedState = loadState();

export const store = configureStore({
  reducer: {
    auth: authReducer,
    teams: teamsReducer,
    leagues: leaguesReducer,
    games: gamesReducer,
    rankings: rankingsReducer,
    settings: settingsReducer,
    feedback: feedbackReducer,
    support: supportReducer,
  },
  preloadedState: persistedState,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().prepend(authErrorMiddleware.middleware),
});

store.subscribe(() => {
  saveState(store.getState());
});

// Wire authFetch's 401 hook into the store. Keeps utils/authFetch.js free of
// any Redux imports — the cycle (store → slice → authFetch → store) cannot
// re-form because authFetch no longer imports anything from this module.
registerOnUnauthorized(() => store.dispatch(sessionExpired()));