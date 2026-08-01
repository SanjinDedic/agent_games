import React, { useState } from 'react';
import usePyodideHealth from '../hooks/usePyodideHealth';

// Small execution-path indicator: green when the in-browser Python runtime
// (Pyodide) booted AND passed its health probe, orange when runs go through
// the Celery fallback (probe/boot failed, or Pyodide is switched off), grey
// pulse while booting/probing. Hover explains. Same fixed-position tooltip
// trick as StrategyTooltip so overflow wrappers can't clip it.
const PyodideStatusDot = ({ className = '' }) => {
    const { state, failureReason, pyodideEnabled } = usePyodideHealth();
    const [pos, setPos] = useState(null);

    let color, label, explanation;
    if (!pyodideEnabled) {
        color = 'bg-notice-orange';
        label = 'Code runs on the server';
        explanation =
            'In-browser Python is turned off. Your code runs on the server.';
    } else if (state === 'failed') {
        color = 'bg-notice-orange';
        label = 'Code runs on the server';
        explanation =
            `In-browser Python is unavailable (${failureReason}). ` +
            'Your code still works — it runs on the server instead.';
    } else if (state === 'ready' || state === 'running') {
        color = 'bg-success';
        label = 'Code runs in your browser';
        explanation =
            'Python runs directly in your browser — startup check passed. ' +
            'Code executes instantly, no server round-trip.';
    } else {
        // idle | booting | probing
        color = 'bg-ui-light animate-pulse';
        label = 'Checking browser Python';
        explanation =
            'Starting the in-browser Python runtime and verifying it works…';
    }

    const show = (e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        setPos({
            top: rect.bottom + 6,
            left: Math.min(rect.left, window.innerWidth - 300),
        });
    };

    return (
        <span
            className={`cursor-help inline-flex flex-shrink-0 items-center ${className}`}
            onMouseEnter={show}
            onMouseLeave={() => setPos(null)}
        >
            <span
                className={`w-2.5 h-2.5 rounded-full ${color}`}
                role="status"
                aria-label={label}
            />
            {pos && (
                <span
                    className="pointer-events-none fixed z-50 w-72 max-w-[80vw] rounded-lg bg-ui-dark p-3 text-sm font-normal normal-case text-white shadow-lg"
                    style={{ top: pos.top, left: pos.left }}
                >
                    {explanation}
                </span>
            )}
        </span>
    );
};

export default PyodideStatusDot;
