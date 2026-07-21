import React from 'react';

/**
 * One cell of the student x exercise matrix.
 * status: 'passed' | 'attempted' | 'untouched'; attempts shown for attempted
 * cells so "stuck after N tries" is visible at a glance.
 */
const StatusCell = ({ status, attempts, onClick, title }) => {
  if (status === 'untouched') {
    return (
      <span className="inline-flex w-8 h-8 items-center justify-center text-ui-light select-none">
        ·
      </span>
    );
  }

  const passed = status === 'passed';
  return (
    <button
      onClick={onClick}
      title={title}
      className={`inline-flex w-8 h-8 items-center justify-center rounded-md text-sm font-bold transition-colors ${
        passed
          ? 'bg-green-100 text-green-700 hover:bg-green-200'
          : 'bg-amber-100 text-amber-700 hover:bg-amber-200'
      }`}
    >
      {passed ? '✓' : attempts}
    </button>
  );
};

export default StatusCell;
