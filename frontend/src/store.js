import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import teamsReducer from './slices/teamsSlice';
import leaguesReducer from './slices/leaguesSlice';
import gamesReducer from './slices/gamesSlice.js';
import rankingsReducer from './slices/rankingsSlice';
import settingsReducer from './slices/settingsSlice';

const saveState = (state) => {
  try {
    const serializedState = JSON.stringify(state);
    sessionStorage.setItem('reduxState', serializedState); // Use sessionStorage instead of localStorage
  } catch (e) {
    console.warn('Error saving state to session storage:', e);
  }
};

const loadState = () => {
  try {
    const serializedState = sessionStorage.getItem('reduxState'); // Use sessionStorage instead of localStorage
    if (serializedState === null) {
      return undefined; // Let reducers initialize the state
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
  },
  preloadedState: persistedState,
});

store.subscribe(() => {
  saveState(store.getState());
});