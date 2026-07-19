// src/AgentGames/Shared/hooks/useLessonAPI.js
import { useCallback } from 'react';
import { useSelector } from 'react-redux';
import { authFetch } from '../../../utils/authFetch';
import { selectToken } from '../../../slices/authSlice';

/**
 * Hook for the lesson API. Lessons are markdown documents (with runnable
 * ```python-run blocks) opened in a modal via lesson://<slug> links.
 */
export const useLessonAPI = () => {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  /**
   * Shared plumbing: JSON request, and a { success, data | error } result.
   */
  const request = useCallback(async (path, method = 'GET', body = null) => {
    try {
      const options = {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
      };
      if (body !== null) {
        options.body = JSON.stringify(body);
      }
      const response = await authFetch(`${apiUrl}/lesson${path}`, options);
      const data = await response.json();

      if (response.ok) {
        return { success: true, data };
      }
      // 422 validation errors arrive as a list of pydantic error objects.
      const detail = Array.isArray(data.detail)
        ? data.detail.map((err) => err.msg).join('; ')
        : data.detail;
      return { success: false, error: detail || 'Request failed' };
    } catch (error) {
      console.error(`Error calling ${method} ${path}:`, error);
      return { success: false, error: 'Network error' };
    }
  }, [apiUrl, accessToken]);

  /** One lesson by slug, content included (any authenticated role). */
  const getLessonBySlug = useCallback(
    (slug) => request(`/lesson/${encodeURIComponent(slug)}`),
    [request]
  );

  /**
   * Run one lesson code block. Always resolves with the full run result —
   * { status, message, stdout, traceback, duration_ms } — so tracebacks
   * render in the output panel, never toast. A 429 (rate limit) surfaces as
   * { success: false, error }.
   */
  const runSnippet = useCallback(
    (code) => request('/run-snippet', 'POST', { code }),
    [request]
  );

  // ------------------------------------------------------------------
  // Admin content management (admin token required by the backend)
  // ------------------------------------------------------------------

  /** List all lessons without content. */
  const getLessons = useCallback(() => request('/lessons'), [request]);

  /** lesson = { slug, title, content } */
  const createLesson = useCallback(
    (lesson) => request('/lessons', 'POST', lesson),
    [request]
  );

  const updateLesson = useCallback(
    (lessonId, lesson) => request(`/lesson/${lessonId}`, 'PUT', lesson),
    [request]
  );

  const deleteLesson = useCallback(
    (lessonId) => request(`/lesson/${lessonId}`, 'DELETE'),
    [request]
  );

  return {
    getLessonBySlug,
    runSnippet,
    getLessons,
    createLesson,
    updateLesson,
    deleteLesson,
  };
};

export default useLessonAPI;
