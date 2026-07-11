// src/AgentGames/Shared/hooks/useSubmissionWorkspace.js
import { useState, useRef, useCallback } from 'react';
import { toast } from 'react-toastify';

/**
 * Shared state + handlers for a code-submission page (agent submission,
 * tutorial exercises, ...). The page supplies an API adapter and keeps
 * ownership of its domain-specific data loading (league info, exercise
 * definitions, instructions).
 *
 * @param {Object} options
 * @param {Function} options.getLatestSubmission - () => {success, hasSubmission, code}
 * @param {Function} options.getSubmissionHistory - () => {success, submissions, error}
 * @param {Function} options.submitCode - (code, {generateHint}) => {success, output,
 *   feedback, hint, hint_available, hint_cancelled, error}
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
  const [code, setCode] = useState("");
  const [starterCode, setStarterCode] = useState("");
  const [lastSubmission, setLastSubmission] = useState("");
  const [hasLastSubmission, setHasLastSubmission] = useState(false);
  const [output, setOutput] = useState("");
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

  // Update editor reference when mounted
  const handleEditorDidMount = useCallback((editor) => {
    editorRef.current = editor;
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
          setCode(result.code);
        }
        return true;
      }
      if (result.success) {
        setHasLastSubmission(false);
      }
      return false;
    },
    [getLatestSubmission]
  );

  /**
   * Register the starter code once the page has loaded it. With intoEditor
   * (no previous submission) it also becomes the editor content.
   */
  const applyStarterCode = useCallback((starter, { intoEditor = false } = {}) => {
    setStarterCode(starter);
    if (intoEditor) {
      setCode(starter);
    }
  }, []);

  // Submit code to the API
  const handleSubmit = useCallback(async () => {
    if (!code || code.trim() === "") {
      toast.error("Please enter some code before submitting");
      return;
    }

    setOutput("");
    setFeedback("");
    setShouldCollapseInstructions(true);

    const result = await submitCode(code);
    if (result.hint_available && !allowHint) toast.success("A hint is now available");
    setAllowHint(result.hint_available);

    if (result.success) {
      setOutput(result.output);
      setFeedback(result.feedback);

      // Refresh the latest submission info
      await loadLatestSubmission();
    }
  }, [code, allowHint, submitCode, loadLatestSubmission]);

  // Request a hint for the current code (hits the same endpoint with generate_hint=true)
  const handleGetHint = useCallback(async () => {
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
  }, [code, allowHint, submitCode, loadLatestSubmission]);

  // Load last submitted code
  const handleLoadLastSubmission = useCallback(() => {
    if (hasLastSubmission && editorRef.current) {
      editorRef.current.setValue(lastSubmission);
      setCode(lastSubmission);
      toast.success("Loaded last submission");
    } else {
      toast.error("No previous submission found");
    }
  }, [hasLastSubmission, lastSubmission]);

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
  const handleSelectSubmission = useCallback((sub) => {
    if (editorRef.current && sub?.code != null) {
      editorRef.current.setValue(sub.code);
      setCode(sub.code);
      setSubmissionsModalOpen(false);
      toast.success("Submission loaded into editor");
    }
  }, []);

  // Reset code to starter template
  const handleReset = useCallback(() => {
    if (starterCode && editorRef.current) {
      editorRef.current.setValue(starterCode);
      setCode(starterCode);
      toast.success("Code reset to starter template");
    } else {
      toast.error("Starter code template not available");
      onResetUnavailable?.();
    }
  }, [starterCode, onResetUnavailable]);

  return {
    // state the page may need directly
    code,
    setCode,
    output,
    feedback,
    shouldCollapseInstructions,
    hasLastSubmission,
    hasStarterCode: !!starterCode,

    // page-driven data flow
    loadLatestSubmission,
    applyStarterCode,

    // prop bundles for the shared components
    editorProps: {
      code,
      onCodeChange: setCode,
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
