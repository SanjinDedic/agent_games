import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import useLessonAPI from '../Shared/hooks/useLessonAPI';
import CodeEditor from '../Shared/Submission/CodeEditor';
import LessonMarkdown from '../Shared/Lesson/LessonMarkdown';

const BLANK_LESSON_FORM = { slug: '', title: '', content: '' };

// Mirror of the backend SLUG_RE in lesson_models.py.
const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/**
 * Validate the editor form and build the API payload.
 * Returns { payload } or { error } with a message to toast.
 */
const formToPayload = (form) => {
  const slug = form.slug.trim();
  if (!slug) return { error: 'Lesson slug is required' };
  if (!SLUG_RE.test(slug)) {
    return {
      error:
        "Slug must be lowercase words separated by hyphens (e.g. 'loops-basics')",
    };
  }
  if (!form.title.trim()) return { error: 'Lesson title is required' };
  return {
    payload: {
      slug,
      title: form.title.trim(),
      content: form.content,
    },
  };
};

function LessonEditor({ initialForm, isNew, onSave, onCancel }) {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);

  const setField = (name, value) =>
    setForm((prev) => ({ ...prev, [name]: value }));

  const isDirty = Object.keys(initialForm).some(
    (key) => form[key] !== initialForm[key]
  );

  const slugChanged = !isNew && form.slug !== initialForm.slug;

  const handleClose = () => {
    if (isDirty && !window.confirm('You have unsaved changes. Discard them?')) {
      return;
    }
    onCancel();
  };

  const handleSave = async () => {
    const { payload, error } = formToPayload(form);
    if (error) {
      toast.error(error);
      return;
    }
    if (
      slugChanged &&
      !window.confirm(
        `Change the slug from "${initialForm.slug}" to "${payload.slug}"? ` +
          'Existing lesson:// links to the old slug will stop working.'
      )
    ) {
      return;
    }
    setSaving(true);
    await onSave(payload);
    setSaving(false);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="dialog"
      aria-modal="true"
      onClick={handleClose}
    >
      <div
        className="relative bg-white rounded-lg shadow-xl w-[90vw] h-[98vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={handleClose}
          className="absolute top-2 right-3 z-10 text-gray-400 hover:text-gray-600 text-2xl leading-none"
          aria-label="Close"
        >
          ×
        </button>

        <div className="flex-1 min-h-0 flex flex-col gap-3 px-6 pt-4 pb-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pr-8">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Slug (used in lesson:// links)
              </label>
              <input
                type="text"
                value={form.slug}
                onChange={(e) => setField('slug', e.target.value)}
                placeholder="e.g. loops-basics"
                className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {slugChanged && (
                <p className="mt-1 text-xs text-amber-700">
                  Renaming the slug breaks existing lesson:// links to this
                  lesson.
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Title
              </label>
              <input
                type="text"
                value={form.title}
                onChange={(e) => setField('title', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex-1 min-h-0 grid grid-cols-2 gap-4">
            <div className="flex flex-col min-h-0">
              <label className="block text-sm font-medium text-gray-700 mb-1 py-1">
                Content (Markdown)
              </label>
              <div className="flex-1 border border-gray-300 rounded-md overflow-hidden">
                <CodeEditor
                  code={form.content}
                  onCodeChange={(value) => setField('content', value ?? '')}
                  language="markdown"
                  options={{ wordWrap: 'on', lineNumbers: 'off' }}
                />
              </div>
            </div>
            <div className="flex flex-col min-h-0">
              <label className="block text-sm font-medium text-gray-700 mb-1 py-1">
                Live preview — Run buttons work here
              </label>
              <div className="flex-1 border border-gray-300 rounded-md overflow-y-auto p-4 bg-white">
                <LessonMarkdown content={form.content} />
              </div>
            </div>
          </div>

          <p className="text-xs text-gray-500">
            Link to a lesson from any markdown (problems, tutorial
            descriptions, hints, other lessons) with{' '}
            <code className="font-mono">[text](lesson://{form.slug || 'my-slug'})</code>
            . Make a code block runnable with a{' '}
            <code className="font-mono">```python-run</code> fence — students
            can edit it and run it in the sandbox. Use{' '}
            <code className="font-mono">```output-mark</code> with a{' '}
            <code className="font-mono">--- expected ---</code> line to turn it
            into a self-checking mini-task that shows a green tick when the run
            matches the target output. A tutorial_sync push overwrites lesson
            content edited here — pull first to keep edits.
          </p>
        </div>

        <div className="flex gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={handleSave}
            disabled={saving}
            className={`px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200 ${
              saving ? 'opacity-70 cursor-not-allowed' : ''
            }`}
          >
            {saving ? 'Saving...' : isNew ? 'Create Lesson' : 'Save Lesson'}
          </button>
          <button
            onClick={handleClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors duration-200"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

function AdminLessons() {
  const {
    getLessons,
    getLessonBySlug,
    createLesson,
    updateLesson,
    deleteLesson,
  } = useLessonAPI();

  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  // null = closed, { id: null, form } = creating, { id, form } = editing
  const [editing, setEditing] = useState(null);

  const loadLessons = useCallback(async () => {
    const result = await getLessons();
    if (result.success) {
      setLessons(result.data.lessons);
    } else {
      toast.error(result.error);
    }
  }, [getLessons]);

  useEffect(() => {
    (async () => {
      await loadLessons();
      setLoading(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleEdit = async (lesson) => {
    const result = await getLessonBySlug(lesson.slug);
    if (!result.success) {
      toast.error(result.error);
      return;
    }
    setEditing({
      id: lesson.id,
      form: {
        slug: result.data.slug,
        title: result.data.title,
        content: result.data.content,
      },
    });
  };

  const handleDelete = async (lesson) => {
    if (
      !window.confirm(
        `Delete lesson "${lesson.title}"? lesson:// links pointing to it will stop working.`
      )
    ) {
      return;
    }
    const result = await deleteLesson(lesson.id);
    if (!result.success) {
      toast.error(result.error);
      return;
    }
    toast.success('Lesson deleted');
    await loadLessons();
  };

  const handleSave = async (payload) => {
    const result = editing.id
      ? await updateLesson(editing.id, payload)
      : await createLesson(payload);
    if (!result.success) {
      toast.error(result.error);
      return;
    }
    toast.success(editing.id ? 'Lesson saved' : 'Lesson created');
    setEditing(null);
    await loadLessons();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 pt-20 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 pt-20 px-6 pb-12">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-2xl font-bold text-gray-800">Lessons</h1>
            <button
              onClick={() => setEditing({ id: null, form: BLANK_LESSON_FORM })}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200"
            >
              + New Lesson
            </button>
          </div>

          <p className="text-sm text-gray-500 mb-4">
            Lessons are markdown documents opened in a modal from{' '}
            <code className="font-mono">lesson://slug</code> links inside
            exercise problems, tutorial descriptions, and hints. Code blocks
            fenced as <code className="font-mono">```python-run</code> are
            editable and runnable by students;{' '}
            <code className="font-mono">```output-mark</code> blocks add a
            target output and a green tick when it's matched.
          </p>

          {lessons.length === 0 ? (
            <p className="text-sm text-gray-500">
              No lessons yet — create the first one.
            </p>
          ) : (
            <div className="space-y-2">
              {lessons.map((lesson) => (
                <div
                  key={lesson.id}
                  className="flex items-center gap-3 border border-gray-200 rounded-md px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-gray-800 truncate">
                      {lesson.title}
                    </p>
                    <p className="text-xs text-gray-500 font-mono truncate">
                      lesson://{lesson.slug}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      onClick={() => handleEdit(lesson)}
                      className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition-colors duration-200"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(lesson)}
                      className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded-md transition-colors duration-200"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {editing && (
          <LessonEditor
            key={editing.id ?? 'new'}
            initialForm={editing.form}
            isNew={editing.id === null}
            onSave={handleSave}
            onCancel={() => setEditing(null)}
          />
        )}
      </div>
    </div>
  );
}

export default AdminLessons;
