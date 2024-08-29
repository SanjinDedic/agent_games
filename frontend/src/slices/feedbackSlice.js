import { createSlice } from '@reduxjs/toolkit';

const feedbackSlice = createSlice({
  name: 'feedback',
  initialState: {
    content: '',
  },
  reducers: {
    setFeedback: (state, action) => {
      state.content = action.payload;
    },
    clearFeedback: (state) => {
      state.content = '';
    },
  },
});

export const { setFeedback, clearFeedback } = feedbackSlice.actions;
export default feedbackSlice.reducer;