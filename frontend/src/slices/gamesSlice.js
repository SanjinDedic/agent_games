import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  list: ['Greedy Pig'],
  currentGame: null,
};

const gamesSlice = createSlice({
  name: 'games',
  initialState,
  reducers: {
    setGames: (state, action) => {
      state.list = action.payload;
    },
    setCurrentGame: (state, action) => {
      state.currentGame = action.payload;
    },
    addGame: (state, action) => {
      state.list.push(action.payload);
    },
    removeGame: (state, action) => {
      state.list = state.list.filter(game => game !== action.payload);
    },
  },
});

export const { setGames, setCurrentGame, addGame, removeGame } = gamesSlice.actions;
export default gamesSlice.reducer;