// Context for opening lessons from anywhere in the app. Lives in its own
// file so LessonMarkdown (which renders lesson:// links) and
// LessonModalProvider (which renders LessonMarkdown via LessonModal) don't
// import each other in a cycle.
import { createContext, useContext } from 'react';

export const LessonModalContext = createContext({
  stack: [],
  openLesson: () => {},
  back: () => {},
  close: () => {},
});

export const useLessonModal = () => useContext(LessonModalContext);

export default LessonModalContext;
