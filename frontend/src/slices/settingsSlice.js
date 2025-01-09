import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  agentApiUrl: process.env.REACT_APP_AGENT_API_URL,
  showTooltips: false,
};

const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    toggleTooltips: (state) => {
      state.showTooltips = !state.showTooltips;
    },
  },
});

export const { toggleTooltips } = settingsSlice.actions;
export default settingsSlice.reducer;