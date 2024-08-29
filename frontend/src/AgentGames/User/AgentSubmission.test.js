import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import configureStore from 'redux-mock-store';
import AgentSubmission from './AgentSubmission';
import { checkTokenExpiry } from '../../slices/authSlice';

// Mock Redux store
const mockStore = configureStore([]);
let store;

jest.mock('../../slices/authSlice', () => ({
  ...jest.requireActual('../../slices/authSlice'),
  checkTokenExpiry: jest.fn(),
}));

jest.mock('@monaco-editor/react', () => ({
  __esModule: true,
  default: ({ onMount }) => {
    // Simulate the editor mounting
    React.useEffect(() => {
      if (onMount) onMount({}, {});
    }, [onMount]);
    return <textarea data-testid="editor" />;
  },
}));

describe('AgentSubmission Component', () => {
  beforeEach(() => {
    store = mockStore({
      settings: { agentApiUrl: 'http://localhost:8000' },
      leagues: { currentLeague: { game: 'TestGame', name: 'TestLeague' } },
      auth: { token: 'mockToken', currentUser: { name: 'testUser', role: 'student' }, isAuthenticated: true },
    });

    checkTokenExpiry.mockClear();
  });

  test('renders AgentSubmission component correctly', () => {
    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentSubmission />
        </BrowserRouter>
      </Provider>
    );

    // Check if the component elements are rendered
    expect(screen.getByText(/AGENT GAMES CODE SUBMISSION/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Submit Code/i })).toBeInTheDocument();
    expect(screen.getByText(/TEAM: testUser/i)).toBeInTheDocument();
    expect(screen.getByText(/GAME: TestGame/i)).toBeInTheDocument();
    expect(screen.getByText(/LEAGUE: TestLeague/i)).toBeInTheDocument();
  });

  test('shows loading and then results after submit', async () => {
    // Mock fetch response for submission
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ status: 'success', data: { results: 'Test Results' }, message: 'Submission Successful' }),
      })
    );

    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentSubmission />
        </BrowserRouter>
      </Provider>
    );

    fireEvent.click(screen.getByRole('button', { name: /Submit Code/i }));

    // Check for loading state
    expect(screen.getByText(/Submitting.../i)).toBeInTheDocument();

    await waitFor(() => {
      // Check if results are displayed
      expect(screen.getByText(/Test Results/i)).toBeInTheDocument();
    });

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/submit_agent', expect.any(Object));
  });

  test('shows error message on failed submission', async () => {
    // Mock fetch response for failed submission
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ status: 'error', message: 'Submission Failed' }),
      })
    );

    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentSubmission />
        </BrowserRouter>
      </Provider>
    );

    fireEvent.click(screen.getByRole('button', { name: /Submit Code/i }));

    await waitFor(() => {
      expect(screen.getByText(/Submission Failed/i)).toBeInTheDocument();
    });

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/submit_agent', expect.any(Object));
  });

  test('redirects to login if not authenticated', () => {
    store = mockStore({
      settings: { agentApiUrl: 'http://localhost:8000' },
      leagues: { currentLeague: { game: 'TestGame', name: 'TestLeague' } },
      auth: { token: null, currentUser: { name: '', role: '' }, isAuthenticated: false },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <AgentSubmission />
        </BrowserRouter>
      </Provider>
    );

    // Check if the redirection logic was triggered
    expect(checkTokenExpiry).toHaveBeenCalled();
  });
});
