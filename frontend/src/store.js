import { combineReducers, configureStore } from '@reduxjs/toolkit';
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

const rootReducer = combineReducers({
  auth: authReducer,
  teams: teamsReducer,
  leagues: leaguesReducer,
  games: gamesReducer,
  rankings: rankingsReducer,
  settings: settingsReducer,
  feedback: feedbackReducer,
  support: supportReducer,
});

// The persisted blob may have been written by a different build of the app
// (dev branch switches, deploys mid-session), so its slices can be missing
// keys the current reducers rely on — rehydrating such a shape wholesale
// crashes the first component that dereferences an absent field. Merge each
// persisted slice over the reducer's own defaults so every expected key
// exists; a slice whose stored shape no longer matches at all is dropped.
const isPlainObject = (value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

const mergeWithDefaults = (persisted) => {
  if (!isPlainObject(persisted)) return undefined;
  const defaults = rootReducer(undefined, { type: '@@state-defaults-probe' });
  const merged = {};
  for (const sliceName of Object.keys(defaults)) {
    const def = defaults[sliceName];
    const saved = persisted[sliceName];
    merged[sliceName] =
      isPlainObject(def) && isPlainObject(saved) ? { ...def, ...saved } : def;
  }
  return merged;
};

const persistedState = mergeWithDefaults(loadState());

export const store = configureStore({
  reducer: rootReducer,
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