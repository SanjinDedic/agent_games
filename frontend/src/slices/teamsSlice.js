import { createSlice } from '@reduxjs/toolkit';

const teamsSlice = createSlice({
  name: 'teams',
  initialState: {
    list: [],
    currentTeam: null,
  },
  reducers: {
    setTeams: (state, action) => {
      state.list = action.payload;
    },
    setCurrentTeam: (state, action) => {
      state.currentTeam = action.payload;
    },
    addTeam: (state, action) => {
      state.list.push(action.payload);
    },
    removeTeam: (state, action) => {
      state.list = state.list.filter(team => team.id !== action.payload);
    },
    clearTeam: (state, action) => {
      state.currentTeam = null;
    },
  },
});

export const { setTeams, setCurrentTeam, addTeam, removeTeam, clearTeam } = teamsSlice.actions;
export default teamsSlice.reducer;