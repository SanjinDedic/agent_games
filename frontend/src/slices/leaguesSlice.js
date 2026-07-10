import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  list: [],
  currentLeague: null,
  currentLeagueResults: [],
  currentLeagueResultSelected: null,
  currentRewards: null,
  currentRewardSchema: null,
  currentRewardInstructions: '',
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
        institution_name: league.institution_name ?? null,
        school_league: league.school_league ?? false,
        info_markdown: league.info_markdown ?? '',
      }));
      const existing = state.currentLeague
        ? state.list.find(l => l.name === state.currentLeague.name)
        : null;
      if (existing) {
        state.currentLeague = existing;
      } else if (state.list.length > 0) {
        state.currentLeague = state.list[0];
      } else {
        state.currentLeague = null;
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
        institution_name: league.institution_name ?? null,
        school_league: league.school_league ?? false,
        info_markdown: league.info_markdown ?? '',
      });
    },
    updateLeagueInfo: (state, action) => {
      const { league_id, info_markdown } = action.payload;
      const league = state.list.find(l => l.id === league_id);
      if (league) {
        league.info_markdown = info_markdown;
      }
      if (state.currentLeague && state.currentLeague.id === league_id) {
        state.currentLeague.info_markdown = info_markdown;
      }
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
    setRewardMeta: (state, action) => {
      const { schema = null, instructions = '' } = action.payload || {};
      state.currentRewardSchema = schema;
      state.currentRewardInstructions = instructions;
      state.currentRewards = null;
    },
    clearResults: (state) => {
      state.currentLeagueResults = [];
      state.currentLeagueResultSelected = null;
      state.currentPublishLink = null;
    },
    setPublishLink: (state, action) => {
      state.currentPublishLink = action.payload;
      if (state.currentLeagueResultSelected) {
        state.currentLeagueResultSelected.publish_link = action.payload;
        const resultIndex = state.currentLeagueResults.findIndex(
          result => result.id === state.currentLeagueResultSelected.id
        );
        if (resultIndex !== -1) {
          state.currentLeagueResults[resultIndex].publish_link = action.payload;
        }
      }
    },
  },
});

export const {
  setLeagues,
  addLeague,
  setCurrentLeague,
  clearLeagues,
  updateExpiryDate,
  updateLeagueInfo,
  setResults,
  setCurrentSimulation,
  setRewards,
  setRewardMeta,
  clearResults,
  addSimulationResult,
  setPublishLink
} = leaguesSlice.actions;

export default leaguesSlice.reducer;