import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import teamsReducer from './slices/teamsSlice';
import leaguesReducer from './slices/leaguesSlice';
import gamesReducer from './slices/gamesSlice.js';
import rankingsReducer from './slices/rankingsSlice';
import settingsReducer from './slices/settingsSlice';
import feedbackReducer from './slices/feedbackSlice';

const saveState = (state) => {
  try {
    const serializedState = JSON.stringify(state);
    localStorage.setItem('reduxState', serializedState);
  } catch (e) {
    console.warn('Error saving state to local storage:', e);
  }
};

const loadState = () => {
  try {
    const serializedState = localStorage.getItem('reduxState');
    if (serializedState === null) {
      return undefined;
    }
    return JSON.parse(serializedState);
  } catch (e) {
    console.warn('Error loading state from local storage:', e);
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
  },
  preloadedState: persistedState,
});

store.subscribe(() => {
  saveState(store.getState());
});