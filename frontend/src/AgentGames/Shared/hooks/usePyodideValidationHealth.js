import { useEffect, useSyncExternalStore } from 'react';
import {
  ensureValidationRunner,
  getValidationRunnerStatus,
  subscribeValidationRunnerStatus,
} from '../../../pyodide/validationRunnerClient';
import { isValidationSupported } from '../../../pyodide/games/index.js';

/**
 * Live view of the validation runner's health for the current game, shaped
 * for PyodideStatusDotView: { state, failureReason, pyodideEnabled }.
 *
 * Mounting the hook (or switching game) kicks off boot + the game's
 * starter-code probe, so the submission page pays the boot+probe latency
 * up front instead of on the first submit. Per-game derivation on top of
 * the raw runner snapshot:
 * - a game outside the browser engine registry reports as "runs on the
 *   server" (pyodideEnabled: false), same as the kill switch;
 * - a starter-code probe failure for THIS game reports as failed even
 *   though the runner stays alive for other games;
 * - green requires THIS game's probe to have passed — during a re-probe
 *   after a league switch the dot pulses grey.
 */
const usePyodideValidationHealth = (gameName) => {
  const status = useSyncExternalStore(
    subscribeValidationRunnerStatus,
    getValidationRunnerStatus
  );

  useEffect(() => {
    if (gameName) ensureValidationRunner(gameName);
  }, [gameName]);

  if (!gameName || !isValidationSupported(gameName)) {
    return { state: status.state, failureReason: null, pyodideEnabled: false };
  }
  if (status.probeResults[gameName] === 'fail') {
    return {
      state: 'failed',
      failureReason: 'starter code failed in this browser',
      pyodideEnabled: status.pyodideEnabled,
    };
  }
  const provenForGame = status.probeResults[gameName] === 'pass';
  const state =
    (status.state === 'ready' || status.state === 'running') && !provenForGame
      ? 'probing'
      : status.state;
  return {
    state,
    failureReason: status.failureReason,
    pyodideEnabled: status.pyodideEnabled,
  };
};

export default usePyodideValidationHealth;
