import { useEffect, useSyncExternalStore } from 'react';
import {
  ensureRunner,
  getRunnerStatus,
  subscribeRunnerStatus,
} from '../../../pyodide/exerciseRunnerClient';

/**
 * Live view of the Pyodide runner's health for status indicators.
 * Returns { state, failureReason, pyodideEnabled }.
 *
 * Mounting the hook kicks off boot + health probe, so an indicator is live
 * even on pages that never warm-booted the runner themselves (e.g. a lesson
 * modal opened outside the Tutorial page).
 */
const usePyodideHealth = () => {
  const status = useSyncExternalStore(subscribeRunnerStatus, getRunnerStatus);

  useEffect(() => {
    ensureRunner();
  }, []);

  return status;
};

export default usePyodideHealth;
