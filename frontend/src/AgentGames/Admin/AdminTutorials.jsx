import React, { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'react-toastify';
import useTutorialAPI from '../Shared/hooks/useTutorialAPI';
import CodeEditor from '../Shared/Submission/CodeEditor';
import ExerciseResults from '../User/ExerciseResults';

const BLANK_EXERCISE_FORM = {
  title: '',
  entry_function: '',
  problem_markdown: '',
  starter_code: '',
  test_code: '',
  solution: '',
  exercise_hints: [],
};

const exerciseToForm = (exercise) => ({
  title: exercise.title,
  entry_function: exercise.entry_function,
  problem_markdown: exercise.problem_markdown,
  starter_code: exercise.starter_code,
  test_code: exercise.test_code ?? '',
  solution: exercise.solution ?? '',
  exercise_hints: exercise.exercise_hints ?? [],
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
  return {
    payload: {
      title: form.title.trim(),
      entry_function: form.entry_function.trim(),
      problem_markdown: form.problem_markdown,
      starter_code: form.starter_code,
      test_code: form.test_code,
      solution: form.solution,
      exercise_hints: form.exercise_hints,
    },
  };
};

const LEFT_TABS = [
  { key: 'starter_code', label: 'Starter code' },
  { key: 'solution', label: 'Solution (optional)' },
  { key: 'exercise_hints', label: 'Hints' },
];

/**
 * List editor for an exercise's hints (one Markdown string per hint).
 * Students reveal hints one at a time in this order, so it keeps the same
 * move up/down controls as the exercise list. Blank hints are dropped
 * server-side on save.
 */
function HintsEditor({ hints, onChange }) {
  const setHint = (index, value) =>
    onChange(hints.map((hint, i) => (i === index ? value : hint)));

  const removeHint = (index) => onChange(hints.filter((_, i) => i !== index));

  const moveHint = (index, direction) => {
    const target = index + direction;
    if (target < 0 || target >= hints.length) return;
    const next = [...hints];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  return (
    <div className="h-full overflow-y-auto bg-white p-3 space-y-3">
      {hints.length === 0 && (
        <p className="text-sm text-gray-500">
          No hints yet. Students reveal hints one at a time, in this order.
        </p>
      )}
      {hints.map((hint, index) => (
        <div key={index} className="border border-gray-200 rounded-md p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-gray-700">
              Hint {index + 1}
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => moveHint(index, -1)}
                disabled={index === 0}
                className="px-2 py-0.5 text-gray-600 hover:bg-gray-100 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors duration-200"
                title="Move up"
              >
                ▲
              </button>
              <button
                type="button"
                onClick={() => moveHint(index, 1)}
                disabled={index === hints.length - 1}
                className="px-2 py-0.5 text-gray-600 hover:bg-gray-100 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors duration-200"
                title="Move down"
              >
                ▼
              </button>
              <button
                type="button"
                onClick={() => removeHint(index)}
                className="px-2 py-0.5 text-sm text-red-600 hover:bg-red-50 rounded transition-colors duration-200"
              >
                Remove
              </button>
            </div>
          </div>
          <textarea
            value={hint}
            onChange={(e) => setHint(index, e.target.value)}
            rows={3}
            placeholder="Hint text (Markdown)"
            className="w-full px-2 py-1 border border-gray-300 rounded font-mono text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...hints, ''])}
        className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition-colors duration-200"
      >
        + Add hint
      </button>
    </div>
  );
}

/**
 * Dry-run outcome panel. A normal run (even with failing tests) reuses the
 * student-facing ExerciseResults; status "error" means the run never produced
 * test results (unsafe code, crash, broken test script, timeout), and unlike
 * the student view it shows the traceback — the admin is debugging their own
 * test script.
 */
function RunOutcome({ result }) {
  if (result.status !== 'error') {
    return <ExerciseResults data={result} />;
  }
  return (
    <div className="space-y-2">
      <div className="rounded-lg p-4 font-medium text-white bg-danger">
        {result.message}
      </div>
      {result.traceback && (
        <pre className="bg-[#1e1e1e] text-gray-100 rounded-lg p-3 text-sm overflow-x-auto">
          {result.traceback}
        </pre>
      )}
      {result.stdout && (
        <div>
          <h3 className="font-medium text-gray-800 mb-1">Print output</h3>
          <pre className="bg-[#1e1e1e] text-gray-100 rounded-lg p-3 text-sm overflow-x-auto">
            {result.stdout}
          </pre>
        </div>
      )}
    </div>
  );
}

function ExerciseEditor({ initialForm, isNew, onSave, onRun, onCancel }) {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState(null);
  // What the left pane shows: starter_code | solution | exercise_hints.
  // Run executes the visible code tab, so it's disabled on the hints tab.
  const [leftTab, setLeftTab] = useState('starter_code');
  const isHintsTab = leftTab === 'exercise_hints';
  const resultsRef = useRef(null);

  const setField = (name, value) =>
    setForm((prev) => ({ ...prev, [name]: value }));

  const isDirty = Object.keys(initialForm).some(
    (key) => form[key] !== initialForm[key]
  );

  const handleClose = () => {
    if (
      isDirty &&
      !window.confirm('You have unsaved changes. Discard them?')
    ) {
      return;
    }
    onCancel();
  };

  useEffect(() => {
    if (runResult) {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [runResult]);

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

  const handleRun = async () => {
    if (!form.entry_function.trim()) {
      toast.error('Entry function name is required to run tests');
      return;
    }
    setRunning(true);
    setRunResult(null);
    const result = await onRun(
      form[leftTab],
      form.entry_function.trim(),
      form.test_code
    );
    setRunning(false);
    if (!result.success) {
      toast.error(result.error);
      return;
    }
    setRunResult(result.data);
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

        <div className="flex-1 min-h-0 flex flex-col gap-3 overflow-y-auto px-6 pt-4 pb-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pr-8">
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
                Entry function (the function name every submission must define)
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

          <details open={isNew}>
            <summary className="text-sm font-medium text-gray-700 cursor-pointer select-none">
              Problem (Markdown shown to the student)
            </summary>
            <textarea
              value={form.problem_markdown}
              onChange={(e) => setField('problem_markdown', e.target.value)}
              rows={8}
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </details>

          <div className="flex-1 min-h-[18rem] grid grid-cols-2 gap-4">
            <div className="flex flex-col min-h-0">
              <div className="flex items-center justify-between mb-1">
                <div className="flex gap-1">
                  {LEFT_TABS.map((tab) => (
                    <button
                      key={tab.key}
                      type="button"
                      onClick={() => setLeftTab(tab.key)}
                      className={`px-3 py-1 text-sm rounded-md transition-colors duration-150 ${
                        leftTab === tab.key
                          ? 'bg-gray-800 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
                <span className="text-xs text-gray-500">
                  {isHintsTab
                    ? 'Students reveal hints one at a time, in this order'
                    : 'Run executes tests against the visible tab'}
                </span>
              </div>
              <div className="flex-1 border border-gray-300 rounded-md overflow-hidden">
                {isHintsTab ? (
                  <HintsEditor
                    hints={form.exercise_hints}
                    onChange={(hints) => setField('exercise_hints', hints)}
                  />
                ) : (
                  <CodeEditor
                    code={form[leftTab]}
                    onCodeChange={(value) => setField(leftTab, value ?? '')}
                  />
                )}
              </div>
            </div>
            <div className="flex flex-col min-h-0">
              <label className="block text-sm font-medium text-gray-700 mb-1 py-1">
                Test script — test_* functions using check / check_output /
                capture
              </label>
              <div className="flex-1 border border-gray-300 rounded-md overflow-hidden">
                <CodeEditor
                  code={form.test_code}
                  onCodeChange={(value) => setField('test_code', value ?? '')}
                />
              </div>
            </div>
          </div>

          <p className="text-xs text-gray-500">
            Students see the starter code and can reveal the hints — the
            solution and test script stay server-side. Re-running
            seed_tutorial.py overwrites all exercise content, including tests,
            solutions and hints edited here.
          </p>

          {runResult && (
            <div ref={resultsRef}>
              <RunOutcome result={runResult} />
            </div>
          )}
        </div>

        <div className="flex gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={handleRun}
            disabled={running || isHintsTab}
            title={
              isHintsTab
                ? 'Switch to Starter code or Solution to run tests'
                : undefined
            }
            className={`px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors duration-200 ${
              running || isHintsTab ? 'opacity-70 cursor-not-allowed' : ''
            }`}
          >
            {running ? 'Running...' : 'Run Tests'}
          </button>
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

function AdminTutorials() {
  const {
    getTutorials,
    getTutorialAdmin,
    runExerciseTests,
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
                            {exercise.entry_function}()
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
                      onRun={runExerciseTests}
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
