import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import configureStore from 'redux-mock-store';
import AgentLogin from './AgentLogin';
import { login } from '../../slices/authSlice';

// Mock Redux store
const mockStore = configureStore([]);
let store;

jest.mock('jwt-decode', () => () => ({
  sub: 'testUser',
  role: 'student',
  exp: Math.floor(Date.now() / 1000) + 1000, // mock expiry time
}));

describe('AgentLogin Component', () => {
  beforeEach(() => {
    store = mockStore({
      settings: { agentApiUrl: 'http://localhost:8000' },
      auth: { currentUser: { role: null }, isAuthenticated: false },
    });
  });

  test('renders login form correctly', () => {
    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentLogin />
        </BrowserRouter>
      </Provider>
    );

    expect(screen.getByText(/Username:/i)).toBeInTheDocument();
    expect(screen.getByText(/Password:/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  test('shows error message if fields are empty', () => {
    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentLogin />
        </BrowserRouter>
      </Provider>
    );

    fireEvent.click(screen.getByRole('button', { name: /login/i }));
    expect(screen.getByText(/Please Enter all the fields/i)).toBeInTheDocument();
  });

  test('calls login function on successful login', async () => {
    // Mock fetch response
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ status: 'success', data: { access_token: 'testToken' } }),
      })
    );

    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentLogin />
        </BrowserRouter>
      </Provider>
    );

    fireEvent.change(screen.getByRole('textbox', { name: /username/i }), { target: { value: 'testUser' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'password' } });

    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(store.getActions()).toContainEqual(login({ token: 'testToken', name: 'testUser', role: 'student', exp: expect.any(Number) }));
    });

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/team_login', expect.any(Object));
  });

  test('shows error message on failed login', async () => {
    // Mock fetch response for failed login
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ status: 'failed', message: 'Invalid credentials' }),
      })
    );

    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentLogin />
        </BrowserRouter>
      </Provider>
    );

    fireEvent.change(screen.getByRole('textbox', { name: /username/i }), { target: { value: 'wrongUser' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrongPassword' } });

    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument();
    });

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/team_login', expect.any(Object));
  });
});
