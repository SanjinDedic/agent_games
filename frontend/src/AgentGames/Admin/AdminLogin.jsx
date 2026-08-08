import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  setToken,
  selectIsAuthenticated,
  selectIsTokenExpired,
} from '../../slices/authSlice';
import {
  selectSetupRequired,
  selectSiteName,
  setSiteConfig,
} from '../../slices/settingsSlice';
import { useTerms } from '../Shared/terminology';

// One page, two modes. An unclaimed deployment (no admin row) shows the setup
// form; once claimed it shows the login form. Which one is decided by
// setup_required from GET /config, so the deployment's state — not a route or a
// build flag — picks the form.
function AdminLogin() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const siteName = useSelector(selectSiteName);
  const setupRequired = useSelector(selectSetupRequired);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const tokenExpired = useSelector(selectIsTokenExpired);
  const T = useTerms();

  const [credentials, setCredentials] = useState({ name: '', password: '' });
  const [errorMessage, setErrorMessage] = useState('');
  const [shake, setShake] = useState(false);

  useEffect(() => {
    if (isAuthenticated && !tokenExpired) {
      navigate('/Home');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setCredentials((prev) => ({ ...prev, [name]: value }));
    setErrorMessage('');
  };

  const fail = (message) => {
    setShake(true);
    setTimeout(() => setShake(false), 1000);
    setErrorMessage(message);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!credentials.name.trim() || !credentials.password.trim()) {
      fail('Please enter all fields');
      return;
    }
    if (setupRequired && credentials.password.length < 8) {
      fail('Choose a password of at least 8 characters');
      return;
    }

    try {
      const response = await fetch(
        `${apiUrl}${setupRequired ? '/auth/setup' : '/auth/login'}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: credentials.name,
            password: credentials.password,
          }),
        }
      );

      const data = await response.json();
      if (!response.ok) {
        fail(data.detail || 'Login failed');
        return;
      }

      // A team logging in here rather than at /AgentLogin is a wrong-door
      // mistake, not a failure — send them where their token works.
      dispatch(setToken(data.access_token));
      if (setupRequired) {
        dispatch(setSiteConfig({ setup_required: false }));
      }
      navigate(data.role === 'admin' ? '/Home' : '/TeamHome');
    } catch (error) {
      console.error('Error:', error);
      setErrorMessage('An error occurred. Please try again.');
    }
  };

  const inputClasses = `w-full px-4 py-2 text-lg border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary transition-all duration-200
    ${shake ? 'animate-shake border-danger' : 'border-ui-light focus:border-primary'}`;

  return (
    <div className="flex flex-col items-center justify-center min-h-screen pt-16 px-4 bg-ui-lighter">
      <div className="w-full max-w-lg bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold text-ui-dark mb-2 text-center">
          {setupRequired ? `Set up ${siteName}` : 'Login'}
        </h1>
        {setupRequired && (
          <p className="text-ui mb-8 text-center">
            Pick the name and password you will use to run this site. This is
            the only account that can create {T.leagues} and {T.teams} — there
            is no second admin and no password-reset email, so store it
            somewhere safe.
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label htmlFor="admin_name" className="text-xl font-bold text-ui-dark">
              Name:
            </label>
            <input
              type="text"
              id="admin_name"
              name="name"
              autoComplete="username"
              value={credentials.name}
              onChange={handleChange}
              className={inputClasses}
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="admin_password"
              className="text-xl font-bold text-ui-dark"
            >
              Password:
            </label>
            <input
              type="password"
              id="admin_password"
              name="password"
              autoComplete={setupRequired ? 'new-password' : 'current-password'}
              value={credentials.password}
              onChange={handleChange}
              className={inputClasses}
            />
          </div>

          <button
            type="submit"
            className="w-full py-4 px-6 text-lg font-bold text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200"
          >
            {setupRequired ? 'Create account' : 'Login'}
          </button>

          {errorMessage && (
            <p className="text-lg text-danger text-center">{errorMessage}</p>
          )}
        </form>
      </div>
    </div>
  );
}

export default AdminLogin;
