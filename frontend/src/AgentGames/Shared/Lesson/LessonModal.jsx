import React, { useEffect, useState } from 'react';
import LessonMarkdown from './LessonMarkdown';
import { useLessonModal } from './LessonModalContext';
import useLessonAPI from '../hooks/useLessonAPI';

/**
 * The single lesson-modal host, rendered once by LessonModalProvider.
 * Shows the top of the slug stack; lesson→lesson links push onto the stack
 * (Back pops), so a reader can follow references without losing their place.
 */
function LessonModal() {
  const { stack, back, close } = useLessonModal();
  const { getLessonBySlug } = useLessonAPI();
  const [lesson, setLesson] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const topSlug = stack.length > 0 ? stack[stack.length - 1] : null;

  useEffect(() => {
    if (!topSlug) {
      setLesson(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      const result = await getLessonBySlug(topSlug);
      if (cancelled) return;
      setLoading(false);
      if (result.success) {
        setLesson(result.data);
      } else {
        setLesson(null);
        setError(result.error || 'Lesson not found');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [topSlug, getLessonBySlug]);

  if (!topSlug) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      onClick={close}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-5xl w-full h-full flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-6 py-4 border-b border-ui-lighter">
          {stack.length > 1 && (
            <button
              type="button"
              onClick={back}
              className="text-sm text-primary hover:text-primary-hover font-medium flex-shrink-0"
            >
              ← Back
            </button>
          )}
          <h2 className="text-xl font-bold text-ui-dark truncate flex-1">
            {lesson?.title ?? 'Lesson'}
          </h2>
          <button
            type="button"
            onClick={close}
            className="text-ui-dark/60 hover:text-ui-dark text-2xl leading-none flex-shrink-0"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
            </div>
          ) : error ? (
            <div className="text-center py-12 text-ui-dark/70">
              <p className="font-medium">{error}</p>
              <p className="text-sm mt-2">
                This lesson may have been renamed or removed.
              </p>
            </div>
          ) : lesson ? (
            <LessonMarkdown content={lesson.content} />
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default LessonModal;
