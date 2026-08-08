import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { Provider } from 'react-redux';
import { store } from './store';
import { setSiteConfig } from './slices/settingsSlice';
import ErrorBoundary from './components/ErrorBoundary';

// Deploy config (classroom vs competition wording, site name and icon) comes
// from the API, not the build, so one image can serve either audience. Fetched
// once here rather than in a component: it is needed by public pages before any
// login, and re-fetching per mount would flip the vocabulary mid-session.
// Failure is non-fatal — the slice's defaults already hold the backend's own
// defaults, so the app renders rather than blocking on a config request.
fetch(`${import.meta.env.VITE_AGENT_API_URL}/config`)
  .then((response) => (response.ok ? response.json() : null))
  .then((config) => config && store.dispatch(setSiteConfig(config)))
  .catch(() => {});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <Provider store={store}>
      <App />
      </Provider>
    </ErrorBoundary>
  </React.StrictMode>
);
