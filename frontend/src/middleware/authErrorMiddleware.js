import { createAction, createListenerMiddleware } from '@reduxjs/toolkit';
import { logout, selectCurrentUser } from '../slices/authSlice';
import { clearLeagues } from '../slices/leaguesSlice';
import { clearTeam } from '../slices/teamsSlice';

export const sessionExpired = createAction('auth/sessionExpired');

const LOGIN_ROUTES = {
  admin: '/Login',
  student: '/AgentLogin',
  ai_agent: '/AgentLogin',
};

let isLoggingOut = false;

export const authErrorMiddleware = createListenerMiddleware();

authErrorMiddleware.startListening({
  actionCreator: sessionExpired,
  effect: (action, listenerApi) => {
    if (isLoggingOut) return;
    isLoggingOut = true;

    const currentUser = selectCurrentUser(listenerApi.getState());
    const role = currentUser?.role;

    listenerApi.dispatch(logout());
    listenerApi.dispatch(clearLeagues());
    listenerApi.dispatch(clearTeam());

    const redirectTo = LOGIN_ROUTES[role] || '/';
    window.location.href = redirectTo;

    setTimeout(() => {
      isLoggingOut = false;
    }, 1000);
  },
});
