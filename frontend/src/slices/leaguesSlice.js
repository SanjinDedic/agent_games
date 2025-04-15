import { createSlice, createAction } from '@reduxjs/toolkit';

// Define a standalone action creator for setPublishLink to ensure it's properly created
export const setPublishLink = createAction('leagues/setPublishLink');

const initialState = {
  list: [],
  currentLeague: null,
  currentLeagueResults: [],
  currentLeagueResultSelected: null,
  currentRewards: null,
  currentPublishLink: null,
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
        signup_link: league.signup_link,
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
        signup_link: league.signup_link,
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
    clearLeagues: (state) => {
      state.list = [];
      state.currentLeague = null;
      state.currentLeagueResults = [];
      state.currentLeagueResultSelected = null;
      state.currentPublishLink = null;
    },
    setResults: (state, action) => {
      state.currentLeagueResults = action.payload.map(result => ({
        ...result,
        publish_link: result.publish_link || null
      }));
      if (action.payload.length > 0) {
        state.currentLeagueResultSelected = action.payload[0];
      }
    },
    addSimulationResult: (state, action) => {
      const newResult = {
        ...action.payload,
        publish_link: action.payload.publish_link || null
      };
      state.currentLeagueResults.unshift(newResult);
      state.currentLeagueResultSelected = newResult;
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
      state.currentPublishLink = null;
    },
  },
  // Handle the standalone action creator
  extraReducers: (builder) => {
    builder.addCase(setPublishLink, (state, action) => {
      state.currentPublishLink = action.payload;
      
      // Also update the publish_link in the current selected result
      if (state.currentLeagueResultSelected) {
        state.currentLeagueResultSelected.publish_link = action.payload;
        
        // Update the publish_link in the results array as well
        const resultIndex = state.currentLeagueResults.findIndex(
          result => result.id === state.currentLeagueResultSelected.id
        );
        if (resultIndex !== -1) {
          state.currentLeagueResults[resultIndex].publish_link = action.payload;
        }
      }
    });
  }
});

export const { 
  setLeagues, 
  addLeague, 
  setCurrentLeague, 
  clearLeagues, 
  updateExpiryDate, 
  setResults, 
  setCurrentSimulation, 
  setRewards, 
  clearResults, 
  addSimulationResult
} = leaguesSlice.actions;

export default leaguesSlice.reducer;