// src/AgentGames/Shared/hooks/useSubmissionWorkspace.js
import { useState, useRef, useCallback } from 'react';
import { toast } from 'react-toastify';

/**
 * Shared state + handlers for a code-submission page (agent submission,
 * tutorial exercises, ...). The page supplies an API adapter and keeps
 * ownership of its domain-specific data loading (league info, exercise
 * definitions, instructions).
 *
 * The editor content is deliberately NOT React state — it lives in Monaco and
 * is shadowed in a ref (`getCode()`), because nothing renders it and a render
 * per keystroke is what let the library resync the model and throw the caret
 * to the end of the file.
 *
 * @param {Object} options
 * @param {Function} options.getLatestSubmission - () => {success, hasSubmission, code}
 * @param {Function} options.getSubmissionHistory - () => {success, submissions, error}
 * @param {Function} options.submitCode - (code, {generateHint}) => {success, output,
 *   feedback, hint, hint_available, hint_cancelled, error, stdout (error path only;
 *   successful runs carry it inside output)}
 * @param {Function} [options.onResetUnavailable] - called when Reset Code is pressed
 *   but no starter code is loaded, so the page can retry loading it
 * @returns {Object} state, handlers, and per-component prop bundles
 *   (editorProps, footerProps, submissionsModalProps, hintModalProps)
 */
export const useSubmissionWorkspace = ({
  getLatestSubmission,
  getSubmissionHistory,
  submitCode,
  onResetUnavailable,
}) => {
  const [starterCode, setStarterCode] = useState("");
  const [lastSubmission, setLastSubmission] = useState("");
  const [hasLastSubmission, setHasLastSubmission] = useState(false);
  const [output, setOutput] = useState("");
  // Program output (print/stderr) from the last run, kept separate from
  // `output` so failed runs can still surface their partial prints without
  // faking a results object. undefined = no run yet, null = ran silently.
  const [stdout, setStdout] = useState(undefined);
  const [feedback, setFeedback] = useState("");
  const [shouldCollapseInstructions, setShouldCollapseInstructions] =
    useState(false);
  const [submissionsModalOpen, setSubmissionsModalOpen] = useState(false);
  const [submissionHistory, setSubmissionHistory] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [hintModalOpen, setHintModalOpen] = useState(false);
  const [hint, setHint] = useState(null);
  const [isGeneratingHint, setIsGeneratingHint] = useState(false);
  const [allowHint, setAllowHint] = useState(false);
  const editorRef = useRef(null);

  // The editor is uncontrolled: Monaco owns the buffer and this ref shadows it,
  // so a keystroke costs zero renders and nothing ever writes the model back
  // underneath the caret. See CodeEditor for why that matters.
  const codeRef = useRef("");
  // Content that arrived before Monaco mounted (the initial submission fetch
  // resolves independently of mount), applied in handleEditorDidMount.
  const pendingCodeRef = useRef(null);

  // The single writer into the editor buffer — every deliberate replacement
  // (starter code, reset, loading a submission) goes through here.
  const setEditorCode = useCallback((value) => {
    const text = value ?? "";
    codeRef.current = text;
    if (editorRef.current) {
      editorRef.current.setValue(text);
    } else {
      pendingCodeRef.current = text;
    }
  }, []);

  const getCode = useCallback(() => codeRef.current, []);

  // Keep the shadow copy in step with the student's typing. Deliberately does
  // no setState: this runs on every keystroke.
  const handleCodeChange = useCallback((value) => {
    codeRef.current = value ?? "";
  }, []);

  // Update editor reference when mounted
  const handleEditorDidMount = useCallback((editor) => {
    editorRef.current = editor;
    if (pendingCodeRef.current !== null) {
      editor.setValue(pendingCodeRef.current);
      pendingCodeRef.current = null;
    }
  }, []);

  /**
   * Fetch the latest submission and remember it. With intoEditor it also
   * becomes the editor content (initial page load); without, it only
   * refreshes the "Last Submission" button state (after a new submit).
   * Returns whether a submission exists.
   */
  const loadLatestSubmission = useCallback(
    async ({ intoEditor = false } = {}) => {
      const result = await getLatestSubmission();
      if (result.success && result.hasSubmission) {
        setLastSubmission(result.code);
        setHasLastSubmission(true);
        if (intoEditor) {
          setEditorCode(result.code);
        }
        return true;
      }
      if (result.success) {
        setHasLastSubmission(false);
      }
      return false;
    },
    [getLatestSubmission, setEditorCode]
  );

  /**
   * Register the starter code once the page has loaded it. With intoEditor
   * (no previous submission) it also becomes the editor content.
   */
  const applyStarterCode = useCallback(
    (starter, { intoEditor = false } = {}) => {
      setStarterCode(starter);
      if (intoEditor) {
        setEditorCode(starter);
      }
    },
    [setEditorCode]
  );

  // Submit code to the API
  const handleSubmit = useCallback(async () => {
    const code = codeRef.current;
    if (!code || code.trim() === "") {
      toast.error("Please enter some code before submitting");
      return;
    }

    setOutput("");
    setStdout(undefined);
    setFeedback("");
    setShouldCollapseInstructions(true);

    const result = await submitCode(code);
    if (result.hint_available && !allowHint) toast.success("A hint is now available");
    setAllowHint(result.hint_available);
    setStdout(result.success ? result.output?.stdout ?? null : result.stdout);

    if (result.success) {
      setOutput(result.output);
      setFeedback(result.feedback);

      // Refresh the latest submission info
      await loadLatestSubmission();
    }
  }, [allowHint, submitCode, loadLatestSubmission]);

  // Request a hint for the current code (hits the same endpoint with generate_hint=true)
  const handleGetHint = useCallback(async () => {
    const code = codeRef.current;
    if (!code || code.trim() === "") {
      toast.error("Please enter some code before requesting a hint");
      return;
    }

    setIsGeneratingHint(true);
    setHint(null);
    setHintModalOpen(true);

    const result = await submitCode(code, { generateHint: true });

    setIsGeneratingHint(false);

    if (result.hint_available && !allowHint) toast.success("A hint is now available");
    setAllowHint(result.hint_available);

    // A hint only comes back when validation fails — hints exist to help
    // students reach valid code, not to improve a valid agent.
    if (result.hint) {
      setHint(result.hint);
    } else {
      if (result.hint_cancelled) {
        // The edited code passed validation, so no hint was generated or consumed
        toast.success("Submission valid — hint cancelled");
      }
      // otherwise submitCode already surfaced the error via toast
      setHintModalOpen(false);
    }

    if (result.success) {
      // The hint request is a real submission, so refresh the feedback panel too
      setOutput(result.output);
      setFeedback(result.feedback);
      setShouldCollapseInstructions(true);

      await loadLatestSubmission();
    }
  }, [allowHint, submitCode, loadLatestSubmission]);

  // Load last submitted code
  const handleLoadLastSubmission = useCallback(() => {
    if (hasLastSubmission) {
      setEditorCode(lastSubmission);
      toast.success("Loaded last submission");
    } else {
      toast.error("No previous submission found");
    }
  }, [hasLastSubmission, lastSubmission, setEditorCode]);

  // Open submissions modal and load history
  const handleShowSubmissions = useCallback(async () => {
    setSubmissionsModalOpen(true);
    setIsLoadingHistory(true);
    const result = await getSubmissionHistory();
    setIsLoadingHistory(false);
    if (result.success) {
      setSubmissionHistory(result.submissions);
    } else {
      toast.error(result.error || "Failed to load submissions");
      setSubmissionHistory([]);
    }
  }, [getSubmissionHistory]);

  // Load a specific past submission into the editor
  const handleSelectSubmission = useCallback(
    (sub) => {
      if (sub?.code != null) {
        setEditorCode(sub.code);
        setSubmissionsModalOpen(false);
        toast.success("Submission loaded into editor");
      }
    },
    [setEditorCode]
  );

  // Reset code to starter template
  const handleReset = useCallback(() => {
    if (starterCode) {
      setEditorCode(starterCode);
      toast.success("Code reset to starter template");
    } else {
      toast.error("Starter code template not available");
      onResetUnavailable?.();
    }
  }, [starterCode, onResetUnavailable, setEditorCode]);

  return {
    // state the page may need directly
    getCode,
    output,
    stdout,
    feedback,
    shouldCollapseInstructions,
    hasLastSubmission,
    hasStarterCode: !!starterCode,

    // page-driven data flow
    loadLatestSubmission,
    applyStarterCode,

    // prop bundles for the shared components
    editorProps: {
      defaultCode: "",
      onCodeChange: handleCodeChange,
      onMount: handleEditorDidMount,
    },
    footerProps: {
      onSubmit: handleSubmit,
      onGetHint: handleGetHint,
      onLoadLast: handleLoadLastSubmission,
      onReset: handleReset,
      onShowSubmissions: handleShowSubmissions,
      allowHint,
      isGeneratingHint,
      hasLastSubmission,
      hasStarterCode: !!starterCode,
    },
    submissionsModalProps: {
      isOpen: submissionsModalOpen,
      onClose: () => setSubmissionsModalOpen(false),
      submissions: submissionHistory,
      isLoading: isLoadingHistory,
      onSelect: handleSelectSubmission,
    },
    hintModalProps: {
      isOpen: hintModalOpen,
      isLoading: isGeneratingHint,
      hint,
      onClose: () => setHintModalOpen(false),
    },
  };
};

export default useSubmissionWorkspace;
