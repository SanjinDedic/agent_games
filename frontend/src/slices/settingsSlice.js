import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  agentApiUrl: import.meta.env.VITE_AGENT_API_URL,
  immersiveMode: false,
};

const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    setImmersiveMode: (state, action) => {
      state.immersiveMode = action.payload;
    },
  },
});

export const { setImmersiveMode } = settingsSlice.actions;

export const selectImmersiveMode = (state) => state.settings.immersiveMode;

export default settingsSlice.reducer;
