import React from 'react';
import { PyodideStatusDotView } from './PyodideStatusDot';
import usePyodideValidationHealth from '../hooks/usePyodideValidationHealth';

// Execution-path indicator for agent validation: same visual language as
// the exercise dot, fed by the validation runner's per-game health (the
// starter-code probe for the league's game).
const ValidationStatusDot = ({ gameName, className = '' }) => {
    const { state, failureReason, pyodideEnabled } =
        usePyodideValidationHealth(gameName);
    return (
        <PyodideStatusDotView
            state={state}
            failureReason={failureReason}
            pyodideEnabled={pyodideEnabled}
            className={className}
        />
    );
};

export default ValidationStatusDot;
