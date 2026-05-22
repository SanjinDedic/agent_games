import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  agentApiUrl: import.meta.env.VITE_AGENT_API_URL,
};

const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {},
});

export default settingsSlice.reducer;
