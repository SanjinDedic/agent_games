import { createSlice } from '@reduxjs/toolkit';

const supportSlice = createSlice({
  name: 'support',
  initialState: {
    isDialogOpen: false,
  },
  reducers: {
    openSupportDialog: (state) => {
      state.isDialogOpen = true;
    },
    closeSupportDialog: (state) => {
      state.isDialogOpen = false;
    },
  },
});

export const { openSupportDialog, closeSupportDialog } = supportSlice.actions;
export default supportSlice.reducer;
