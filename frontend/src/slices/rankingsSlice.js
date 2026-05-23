import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  allRankings: [],
  currentRanking: null,
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
    clearRankings: (state) => {
      state.currentRanking = null;
    },
  },
});

export const { setRanking, clearRankings, setAllRankings } = rankingsSlice.actions;
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
    if (data.status === 'success') {
      const results = data.data?.all_results || [];
      dispatch(setAllRankings(results));
      return { success: true, results };
    }
    return { success: false, error: data.message || 'Failed to fetch published results' };
  } catch (error) {
    console.error('Error fetching published results:', error);
    return { success: false, error: 'Network error' };
  }
};