import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import configureStore from 'redux-mock-store';
import AgentLeagueSignUp from './AgentLeagueSignUp';
import { checkTokenExpiry } from '../../slices/authSlice';
import { setCurrentLeague, setLeagues } from '../../slices/leaguesSlice';

// Mock Redux store
const mockStore = configureStore([]);
let store;

jest.mock('../../slices/authSlice', () => ({
  ...jest.requireActual('../../slices/authSlice'),
  checkTokenExpiry: jest.fn(),
}));

jest.mock('react-toastify', () => ({
  toast: {
    error: jest.fn(),
    success: jest.fn(),
  },
}));

describe('AgentLeagueSignUp Component', () => {
  beforeEach(() => {
    store = mockStore({
      settings: { agentApiUrl: 'http://localhost:8000' },
      auth: { token: 'mockToken', currentUser: { name: 'testUser', role: 'student' }, isAuthenticated: true },
      leagues: {
        currentLeague: { name: 'TestLeague', game: 'TestGame' },
        list: [
          { id: 1, name: 'TestLeague1', game: 'TestGame1' },
          { id: 2, name: 'TestLeague2', game: 'TestGame2' },
        ],
      },
    });

    checkTokenExpiry.mockClear();
  });

  test('renders AgentLeagueSignUp component correctly', () => {
    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentLeagueSignUp />
        </BrowserRouter>
      </Provider>
    );

    // Check if the component elements are rendered
    expect(screen.getByText(/PICK A LEAGUE TO JOIN/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Join League/i })).toBeInTheDocument();
    expect(screen.getAllByRole('checkbox')).toHaveLength(2); // Two leagues in mock data
  });

  test('displays leagues from API call', async () => {
    // Mock fetch response for get_all_admin_leagues
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ status: 'success', data: { admin_leagues: store.getState().leagues.list } }),
      })
    );

    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentLeagueSignUp />
        </BrowserRouter>
      </Provider>
    );

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/get_all_admin_leagues');
      expect(screen.getByText('TestLeague1')).toBeInTheDocument();
      expect(screen.getByText('TestLeague2')).toBeInTheDocument();
    });
  });

  test('handles league selection', () => {
    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentLeagueSignUp />
        </BrowserRouter>
      </Provider>
    );

    // Simulate selecting a league
    fireEvent.click(screen.getByLabelText(/TestLeague1/i));
    expect(store.getActions()).toContainEqual(setCurrentLeague('TestLeague1'));
  });

  test('handles sign up for a league', async () => {
    // Mock fetch response for league_assign
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ status: 'success', message: 'Successfully joined the league' }),
      })
    );

    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentLeagueSignUp />
        </BrowserRouter>
      </Provider>
    );

    fireEvent.click(screen.getByRole('button', { name: /Join League/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/league_assign', expect.any(Object));
      expect(screen.getByText(/Successfully joined the league/i)).toBeInTheDocument();
    });
  });

  test('redirects to login if not authenticated', () => {
    store = mockStore({
      settings: { agentApiUrl: 'http://localhost:8000' },
      auth: { token: null, currentUser: { name: '', role: '' }, isAuthenticated: false },
      leagues: {
        currentLeague: { name: '', game: '' },
        list: [],
      },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentLeagueSignUp />
        </BrowserRouter>
      </Provider>
    );

    expect(checkTokenExpiry).toHaveBeenCalled();
  });

  test('shows error when league is not selected', () => {
    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentLeagueSignUp />
        </BrowserRouter>
      </Provider>
    );

    // Clear current league selection
    store = mockStore({
      settings: { agentApiUrl: 'http://localhost:8000' },
      auth: { token: 'mockToken', currentUser: { name: 'testUser', role: 'student' }, isAuthenticated: true },
      leagues: {
        currentLeague: { name: '', game: '' },
        list: [
          { id: 1, name: 'TestLeague1', game: 'TestGame1' },
          { id: 2, name: 'TestLeague2', game: 'TestGame2' },
        ],
      },
    });

    fireEvent.click(screen.getByRole('button', { name: /Join League/i }));

    expect(screen.getByText(/League not selected/i)).toBeInTheDocument();
  });
});
