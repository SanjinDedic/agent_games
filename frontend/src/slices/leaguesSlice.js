import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  list: [],
  currentLeague: null,
  currentLeagueResults: [],
  currentLeagueResultSelected: null,
  currentRewards: null,
};

const leaguesSlice = createSlice({
  name: 'leagues',
  initialState,
  reducers: {
    setLeagues: (state, action) => {
      state.list = action.payload.map(league => ({
        created_date: league.created_date,
        expiry_date: league.expiry_date,
        game: league.game,
        id: league.id,
        name: league.name,
        signup_link: league.signup_link,  // Add this line to store the signup_link
      }));
      if (action.payload.length > 0) {
        state.currentLeague = state.list[0];
      }
    },
    addLeague: (state, action) => {
      const league = action.payload;
      state.list.push({
        created_date: league.created_date,
        expiry_date: league.expiry_date,
        game: league.game,
        id: league.id,
        name: league.name,
      });
    },
    updateExpiryDate: (state, action) => {
      const { name, expiry_date } = action.payload;
      const league = state.list.find(league => league.name === name);
      if (league) {
        league.expiry_date = expiry_date;
      }
      if (state.currentLeague && state.currentLeague.name === name) {
        state.currentLeague.expiry_date = expiry_date;
      }
    },
    setCurrentLeague: (state, action) => {
      const league = state.list.find(league => league.name === action.payload);
      if (league) {
        state.currentLeague = league;
      }
    },
    clearLeagues: (state, action) => {
      state.list = [];
      state.currentLeague = null;
    },
    setResults: (state, action) => {
      state.currentLeagueResults = action.payload;
      if (action.payload.length > 0) {
        state.currentLeagueResultSelected = action.payload[0];
      }
    },
    addSimulationResult: (state, action) => {
      state.currentLeagueResults.unshift(action.payload);
      state.currentLeagueResultSelected = action.payload;
    },
    setCurrentSimulation: (state, action) => {
      const timestamp = state.currentLeagueResults.find(league => league.timestamp === action.payload);
      if (timestamp) {
        state.currentLeagueResultSelected = timestamp;
      }
    },
    setRewards: (state, action) => {
      state.currentRewards = action.payload;
    },
    clearResults: (state) => {
      state.currentLeagueResults = [];
      state.currentLeagueResultSelected = null;
    },
  },
});

export const { setLeagues, addLeague, setCurrentLeague, clearLeagues, updateExpiryDate, setResults, setCurrentSimulation, setRewards, clearResults, addSimulationResult } = leaguesSlice.actions;
export default leaguesSlice.reducer;