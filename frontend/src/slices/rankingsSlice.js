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