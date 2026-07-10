import { createSlice } from '@reduxjs/toolkit';
import { authFetch } from '../utils/authFetch';

const initialState = {
  allRankings: [],
  currentRanking: null,
  myLeagueRankings: [],
  myLeagueName: null,
  myLeagueInfoMarkdown: '',
};

const rankingsSlice = createSlice({
  name: 'rankings',
  initialState,
  reducers: {
    setRanking: (state, action) => {
      const league = state.allRankings.find(league => league.league_name === action.payload);
        if (league) {
          state.currentRanking = league;
        }

    },
    setAllRankings: (state, action) => {
      state.allRankings = action.payload;
      if (action.payload.length > 0) {
        state.currentRanking = action.payload[0];
      }
    },
    setMyLeagueRankings: (state, action) => {
      const { all_results = [], league_name = null, info_markdown = '' } = action.payload || {};
      state.myLeagueRankings = all_results;
      state.myLeagueName = league_name;
      state.myLeagueInfoMarkdown = info_markdown;
    },
    clearRankings: (state) => {
      state.currentRanking = null;
    },
  },
});

export const {
  setRanking,
  clearRankings,
  setAllRankings,
  setMyLeagueRankings,
} = rankingsSlice.actions;
export default rankingsSlice.reducer;

/**
 * Fetch published results for all leagues if not already cached.
 * Both Leaderboards and AgentRankings call this — whichever mounts first
 * makes the network call, the other reads from Redux.
 */
export const fetchAllRankings = ({ force = false } = {}) => async (dispatch, getState) => {
  const { allRankings } = getState().rankings;
  if (!force && allRankings.length > 0) {
    return { success: true, results: allRankings };
  }
  const apiUrl = getState().settings.agentApiUrl;
  try {
    const response = await fetch(`${apiUrl}/user/get-published-results-for-all-leagues`);
    const data = await response.json();
    if (response.ok) {
      const results = data.all_results || [];
      dispatch(setAllRankings(results));
      return { success: true, results };
    }
    return { success: false, error: data.detail || 'Failed to fetch published results' };
  } catch (error) {
    console.error('Error fetching published results:', error);
    return { success: false, error: 'Network error' };
  }
};

/**
 * Fetch all published results scoped to the logged-in team's league.
 * Server reads league_id from the JWT — no cross-league leakage.
 */
export const fetchMyLeagueRankings = ({ force = false } = {}) => async (dispatch, getState) => {
  const state = getState();
  const { myLeagueRankings, myLeagueName } = state.rankings;
  if (!force && (myLeagueRankings.length > 0 || myLeagueName)) {
    return { success: true, results: myLeagueRankings };
  }
  const apiUrl = state.settings.agentApiUrl;
  const accessToken = state.auth.token;
  if (!accessToken) {
    return { success: false, error: 'Not authenticated' };
  }
  try {
    const response = await authFetch(
      `${apiUrl}/user/get-all-published-results-for-my-league`,
      { headers: { Authorization: `Bearer ${accessToken}` } },
    );
    const data = await response.json();
    if (response.ok) {
      dispatch(setMyLeagueRankings(data || {}));
      return { success: true, results: data?.all_results || [] };
    }
    return { success: false, error: data.detail || 'Failed to fetch published results' };
  } catch (error) {
    console.error('Error fetching my league published results:', error);
    return { success: false, error: 'Network error' };
  }
};
