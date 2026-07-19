import React, { useCallback, useMemo, useState } from 'react';
import { LessonModalContext } from './LessonModalContext';
import LessonModal from './LessonModal';

/**
 * App-level provider for the lesson modal. Wraps the app once (App.jsx) so
 * any LessonMarkdown — in the exercise instructions panel, a tutorial
 * description, the admin preview, or an open lesson itself — can call
 * openLesson(slug). State is a slug stack: lesson→lesson links push, Back
 * pops, Close clears.
 */
function LessonModalProvider({ children }) {
  const [stack, setStack] = useState([]);

  const openLesson = useCallback((slug) => {
    if (!slug) return;
    setStack((prev) =>
      prev[prev.length - 1] === slug ? prev : [...prev, slug]
    );
  }, []);

  const back = useCallback(() => {
    setStack((prev) => prev.slice(0, -1));
  }, []);

  const close = useCallback(() => {
    setStack([]);
  }, []);

  const value = useMemo(
    () => ({ stack, openLesson, back, close }),
    [stack, openLesson, back, close]
  );

  return (
    <LessonModalContext.Provider value={value}>
      {children}
      <LessonModal />
    </LessonModalContext.Provider>
  );
}

export default LessonModalProvider;
