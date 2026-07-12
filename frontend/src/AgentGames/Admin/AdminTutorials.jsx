import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import useTutorialAPI from '../Shared/hooks/useTutorialAPI';
import CodeEditor from '../Shared/Submission/CodeEditor';

const BLANK_EXERCISE_FORM = {
  title: '',
  entry_function: '',
  problem_markdown: '',
  starter_code: '',
  testCases: [{ name: '', argsText: '[]', expectedText: 'null' }],
};

// Test cases are edited as JSON text fields; convert to/from the API shape.
const exerciseToForm = (exercise) => ({
  title: exercise.title,
  entry_function: exercise.entry_function,
  problem_markdown: exercise.problem_markdown,
  starter_code: exercise.starter_code,
  testCases: exercise.test_cases.map((testCase) => ({
    name: testCase.name,
    argsText: JSON.stringify(testCase.args),
    expectedText: JSON.stringify(testCase.expected),
  })),
});

/**
 * Validate the editor form and build the API payload.
 * Returns { payload } or { error } with a message to toast.
 */
const formToPayload = (form) => {
  if (!form.title.trim()) return { error: 'Exercise title is required' };
  if (!form.entry_function.trim()) {
    return { error: 'Entry function name is required' };
  }
  if (!form.problem_markdown.trim()) {
    return { error: 'Problem markdown is required' };
  }
  const test_cases = [];
  for (let i = 0; i < form.testCases.length; i++) {
    const testCase = form.testCases[i];
    if (!testCase.name.trim()) {
      return { error: `Test case ${i + 1} needs a name` };
    }
    let args;
    try {
      args = JSON.parse(testCase.argsText);
    } catch {
      return { error: `Test case ${i + 1}: args is not valid JSON` };
    }
    if (!Array.isArray(args)) {
      return { error: `Test case ${i + 1}: args must be a JSON list, e.g. [1, 2]` };
    }
    let expected;
    try {
      expected = JSON.parse(testCase.expectedText);
    } catch {
      return { error: `Test case ${i + 1}: expected is not valid JSON` };
    }
    test_cases.push({ name: testCase.name.trim(), args, expected });
  }
  if (test_cases.length === 0) {
    return { error: 'An exercise needs at least one test case' };
  }
  return {
    payload: {
      title: form.title.trim(),
      entry_function: form.entry_function.trim(),
      problem_markdown: form.problem_markdown,
      starter_code: form.starter_code,
      test_cases,
    },
  };
};

function ExerciseEditor({ initialForm, isNew, onSave, onCancel }) {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);

  const setField = (name, value) =>
    setForm((prev) => ({ ...prev, [name]: value }));

  const setTestCaseField = (index, name, value) =>
    setForm((prev) => ({
      ...prev,
      testCases: prev.testCases.map((testCase, i) =>
        i === index ? { ...testCase, [name]: value } : testCase
      ),
    }));

  const addTestCase = () =>
    setForm((prev) => ({
      ...prev,
      testCases: [
        ...prev.testCases,
        { name: '', argsText: '[]', expectedText: 'null' },
      ],
    }));

  const removeTestCase = (index) =>
    setForm((prev) => ({
      ...prev,
      testCases: prev.testCases.filter((_, i) => i !== index),
    }));

  const handleSave = async () => {
    const { payload, error } = formToPayload(form);
    if (error) {
      toast.error(error);
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
      onClick={onCancel}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-[90vw] h-[98vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-800">
            {isNew ? 'New Exercise' : `Edit Exercise: ${initialForm.title}`}
          </h3>
          <button
            type="button"
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Entry function (the function name the tests call)
              </label>
              <input
                type="text"
                value={form.entry_function}
                onChange={(e) => setField('entry_function', e.target.value)}
                placeholder="e.g. get_banked"
                className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Problem (Markdown shown to the student)
            </label>
            <textarea
              value={form.problem_markdown}
              onChange={(e) => setField('problem_markdown', e.target.value)}
              rows={10}
              className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Starter code
            </label>
            <div className="h-56 border border-gray-300 rounded-md overflow-hidden">
              <CodeEditor
                code={form.starter_code}
                onCodeChange={(value) => setField('starter_code', value ?? '')}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Test cases — params is a JSON list of arguments, return is the
                expected JSON return value
              </label>
              <button
                onClick={addTestCase}
                className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition-colors duration-200"
              >
                + Add test case
              </button>
            </div>
            <div className="hidden md:flex gap-2 mb-1 text-xs font-medium text-gray-500">
              <span className="flex-[3]">Exercise name</span>
              <span className="flex-[5]">Function params</span>
              <span className="flex-[2]">Function return</span>
              <span className="w-20 flex-shrink-0" />
            </div>
            <div className="space-y-2">
              {form.testCases.map((testCase, index) => (
                <div
                  key={index}
                  className="flex flex-col md:flex-row gap-2 items-stretch md:items-center"
                >
                  <input
                    type="text"
                    value={testCase.name}
                    onChange={(e) => setTestCaseField(index, 'name', e.target.value)}
                    placeholder="Test name"
                    className="flex-[3] min-w-0 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <input
                    type="text"
                    value={testCase.argsText}
                    onChange={(e) => setTestCaseField(index, 'argsText', e.target.value)}
                    placeholder='e.g. [{"Alice": 30}, "Alice"]'
                    className="flex-[5] min-w-0 px-2 py-1 border border-gray-300 rounded font-mono text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <input
                    type="text"
                    value={testCase.expectedText}
                    onChange={(e) =>
                      setTestCaseField(index, 'expectedText', e.target.value)
                    }
                    placeholder="e.g. 30"
                    className="flex-[2] min-w-0 px-2 py-1 border border-gray-300 rounded font-mono text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => removeTestCase(index)}
                    className="w-20 flex-shrink-0 px-2 py-1 text-sm text-red-600 hover:bg-red-50 rounded transition-colors duration-200"
                    title="Remove test case"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={handleSave}
            disabled={saving}
            className={`px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200 ${
              saving ? 'opacity-70 cursor-not-allowed' : ''
            }`}
          >
            {saving ? 'Saving...' : isNew ? 'Create Exercise' : 'Save Exercise'}
          </button>
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors duration-200"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

function AdminTutorials() {
  const {
    getTutorials,
    getTutorialAdmin,
    createTutorial,
    updateTutorial,
    deleteTutorial,
    createExercise,
    updateExercise,
    deleteExercise,
    reorderExercises,
  } = useTutorialAPI();

  const [tutorials, setTutorials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [showNewTutorial, setShowNewTutorial] = useState(false);
  const [newTutorial, setNewTutorial] = useState({ title: '', description: '' });
  const [meta, setMeta] = useState({ title: '', description: '' });
  const [savingMeta, setSavingMeta] = useState(false);
  // null = closed, { id: null } = creating, { id, form } = editing
  const [editing, setEditing] = useState(null);

  const loadTutorials = useCallback(async () => {
    const result = await getTutorials();
    if (result.success) {
      setTutorials(result.tutorials);
      return result.tutorials;
    }
    toast.error(result.error);
    return [];
  }, [getTutorials]);

  const loadDetail = useCallback(
    async (tutorialId) => {
      const result = await getTutorialAdmin(tutorialId);
      if (result.success) {
        setDetail(result.data);
        setMeta({
          title: result.data.title,
          description: result.data.description,
        });
      } else {
        toast.error(result.error);
        setDetail(null);
      }
    },
    [getTutorialAdmin]
  );

  useEffect(() => {
    (async () => {
      const list = await loadTutorials();
      if (list.length > 0) {
        setSelectedId(list[0].id);
      }
      setLoading(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedId !== null) {
      setEditing(null);
      loadDetail(selectedId);
    } else {
      setDetail(null);
    }
  }, [selectedId, loadDetail]);

  const handleCreateTutorial = async () => {
    if (!newTutorial.title.trim()) {
      toast.error('Tutorial title is required');
      return;
    }
    const result = await createTutorial(
      newTutorial.title.trim(),
      newTutorial.description
    );
    if (!result.success) {
      toast.error(result.error);
      return;
    }
    toast.success('Tutorial created');
    setNewTutorial({ title: '', description: '' });
    setShowNewTutorial(false);
    await loadTutorials();
    setSelectedId(result.data.id);
  };

  const handleDeleteTutorial = async (tutorial) => {
    if (
      !window.confirm(
        `Delete tutorial "${tutorial.title}"? This deletes its ${tutorial.exercise_count} exercise(s) and all student submission history for them.`
      )
    ) {
      return;
    }
    const result = await deleteTutorial(tutorial.id);
    if (!result.success) {
      toast.error(result.error);
      return;
    }
    toast.success('Tutorial deleted');
    const list = await loadTutorials();
    setSelectedId(list.length > 0 ? list[0].id : null);
  };

  const handleSaveMeta = async () => {
    if (!meta.title.trim()) {
      toast.error('Tutorial title is required');
      return;
    }
    setSavingMeta(true);
    const result = await updateTutorial(
      selectedId,
      meta.title.trim(),
      meta.description
    );
    setSavingMeta(false);
    if (!result.success) {
      toast.error(result.error);
      return;
    }
    toast.success('Tutorial saved');
    await loadTutorials();
    await loadDetail(selectedId);
  };

  const handleMoveExercise = async (index, direction) => {
    const ids = detail.exercises.map((exercise) => exercise.id);
    const target = index + direction;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    const result = await reorderExercises(selectedId, ids);
    if (result.success) {
      setDetail(result.data);
    } else {
      toast.error(result.error);
      await loadDetail(selectedId);
    }
  };

  const handleDeleteExercise = async (exercise) => {
    if (
      !window.confirm(
        `Delete exercise "${exercise.title}"? This also deletes all student submission history for it.`
      )
    ) {
      return;
    }
    const result = await deleteExercise(exercise.id);
    if (!result.success) {
      toast.error(result.error);
      return;
    }
    toast.success('Exercise deleted');
    if (editing?.id === exercise.id) setEditing(null);
    await loadDetail(selectedId);
    await loadTutorials();
  };

  const handleSaveExercise = async (payload) => {
    const result = editing.id
      ? await updateExercise(editing.id, payload)
      : await createExercise(selectedId, payload);
    if (!result.success) {
      toast.error(result.error);
      return;
    }
    toast.success(editing.id ? 'Exercise saved' : 'Exercise created');
    setEditing(null);
    await loadDetail(selectedId);
    await loadTutorials();
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
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Tutorial list */}
          <div className="lg:w-80 flex-shrink-0">
            <div className="bg-white rounded-lg shadow-md p-4">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800">Tutorials</h2>
                <button
                  onClick={() => setShowNewTutorial((prev) => !prev)}
                  className="px-3 py-1 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200"
                >
                  {showNewTutorial ? 'Close' : '+ New'}
                </button>
              </div>

              {showNewTutorial && (
                <div className="mb-4 p-3 border border-blue-200 rounded-md bg-blue-50 space-y-2">
                  <input
                    type="text"
                    value={newTutorial.title}
                    onChange={(e) =>
                      setNewTutorial((prev) => ({ ...prev, title: e.target.value }))
                    }
                    placeholder="Tutorial title"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <textarea
                    value={newTutorial.description}
                    onChange={(e) =>
                      setNewTutorial((prev) => ({
                        ...prev,
                        description: e.target.value,
                      }))
                    }
                    placeholder="Description"
                    rows={3}
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    onClick={handleCreateTutorial}
                    className="w-full px-3 py-1 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200"
                  >
                    Create Tutorial
                  </button>
                </div>
              )}

              {tutorials.length === 0 ? (
                <p className="text-sm text-gray-500">
                  No tutorials yet — create one to get started.
                </p>
              ) : (
                <ul className="space-y-1">
                  {tutorials.map((tutorial) => (
                    <li key={tutorial.id}>
                      <div
                        className={`flex items-center justify-between rounded-md px-3 py-2 cursor-pointer transition-colors duration-150 ${
                          tutorial.id === selectedId
                            ? 'bg-blue-100 text-blue-800'
                            : 'hover:bg-gray-100 text-gray-700'
                        }`}
                        onClick={() => setSelectedId(tutorial.id)}
                      >
                        <div className="min-w-0">
                          <p className="font-medium truncate">{tutorial.title}</p>
                          <p className="text-xs text-gray-500">
                            {tutorial.exercise_count} exercise
                            {tutorial.exercise_count === 1 ? '' : 's'}
                          </p>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteTutorial(tutorial);
                          }}
                          className="ml-2 px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded transition-colors duration-200 flex-shrink-0"
                        >
                          Delete
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Selected tutorial */}
          <div className="flex-1 min-w-0">
            {!detail ? (
              <div className="bg-white rounded-lg shadow-md p-8 text-center text-gray-500">
                Select or create a tutorial to edit it.
              </div>
            ) : (
              <div className="space-y-6">
                {/* Tutorial meta */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h1 className="text-2xl font-bold text-gray-800">
                      Edit Tutorial
                    </h1>
                    <button
                      onClick={handleSaveMeta}
                      disabled={savingMeta}
                      className={`px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200 ${
                        savingMeta ? 'opacity-70 cursor-not-allowed' : ''
                      }`}
                    >
                      {savingMeta ? 'Saving...' : 'Save Tutorial'}
                    </button>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Title
                      </label>
                      <input
                        type="text"
                        value={meta.title}
                        onChange={(e) =>
                          setMeta((prev) => ({ ...prev, title: e.target.value }))
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Description
                      </label>
                      <textarea
                        value={meta.description}
                        onChange={(e) =>
                          setMeta((prev) => ({
                            ...prev,
                            description: e.target.value,
                          }))
                        }
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Exercises */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold text-gray-800">Exercises</h2>
                    <button
                      onClick={() =>
                        setEditing({ id: null, form: BLANK_EXERCISE_FORM })
                      }
                      className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200"
                    >
                      + Add Exercise
                    </button>
                  </div>

                  {detail.exercises.length === 0 && !editing && (
                    <p className="text-sm text-gray-500">
                      No exercises yet — add the first one.
                    </p>
                  )}

                  <div className="space-y-2 mb-4">
                    {detail.exercises.map((exercise, index) => (
                      <div
                        key={exercise.id}
                        className={`flex items-center gap-3 border rounded-md px-4 py-3 ${
                          editing?.id === exercise.id
                            ? 'border-blue-400 bg-blue-50'
                            : 'border-gray-200'
                        }`}
                      >
                        <span className="text-sm font-mono text-gray-400 w-6 text-right flex-shrink-0">
                          {index + 1}.
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-gray-800 truncate">
                            {exercise.title}
                          </p>
                          <p className="text-xs text-gray-500 font-mono truncate">
                            {exercise.entry_function}() ·{' '}
                            {exercise.test_cases.length} test case
                            {exercise.test_cases.length === 1 ? '' : 's'}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <button
                            onClick={() => handleMoveExercise(index, -1)}
                            disabled={index === 0}
                            className="px-2 py-1 text-gray-600 hover:bg-gray-100 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors duration-200"
                            title="Move up"
                          >
                            ▲
                          </button>
                          <button
                            onClick={() => handleMoveExercise(index, 1)}
                            disabled={index === detail.exercises.length - 1}
                            className="px-2 py-1 text-gray-600 hover:bg-gray-100 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors duration-200"
                            title="Move down"
                          >
                            ▼
                          </button>
                          <button
                            onClick={() =>
                              setEditing({
                                id: exercise.id,
                                form: exerciseToForm(exercise),
                              })
                            }
                            className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition-colors duration-200"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteExercise(exercise)}
                            className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded-md transition-colors duration-200"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {editing && (
                    <ExerciseEditor
                      key={editing.id ?? 'new'}
                      initialForm={editing.form}
                      isNew={editing.id === null}
                      onSave={handleSaveExercise}
                      onCancel={() => setEditing(null)}
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AdminTutorials;
