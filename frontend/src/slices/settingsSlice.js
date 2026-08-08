import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  agentApiUrl: import.meta.env.VITE_AGENT_API_URL,
  immersiveMode: false,
  // Deploy config from GET /config. siteMode defaults to the backend's own
  // default rather than null: useTerms() runs on the first paint, before the
  // fetch resolves, and must never render an undefined noun.
  siteMode: 'competition',
  siteName: 'Agent Games',
  siteIcon: null,
  setupRequired: false,
};

const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    setImmersiveMode: (state, action) => {
      state.immersiveMode = action.payload;
    },
    setSiteConfig: (state, action) => {
      const { site_mode, site_name, site_icon, setup_required } = action.payload;
      if (site_mode) state.siteMode = site_mode;
      if (site_name) state.siteName = site_name;
      if (site_icon !== undefined) state.siteIcon = site_icon ?? null;
      if (setup_required !== undefined) state.setupRequired = setup_required;
    },
  },
});

export const { setImmersiveMode, setSiteConfig } = settingsSlice.actions;

export const selectImmersiveMode = (state) => state.settings.immersiveMode;
export const selectSiteMode = (state) => state.settings.siteMode;
export const selectSiteName = (state) => state.settings.siteName;
export const selectSiteIcon = (state) => state.settings.siteIcon;
export const selectSetupRequired = (state) => state.settings.setupRequired;
export const selectIsClassroom = (state) =>
  state.settings.siteMode === 'classroom';

export default settingsSlice.reducer;
