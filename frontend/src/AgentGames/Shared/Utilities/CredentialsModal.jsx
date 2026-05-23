import React, { useState } from "react";

function CredentialsModal({ teamName, password, onDismiss, dismissLabel = "I've Saved My Credentials" }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h2 className="text-2xl font-bold text-danger text-center mb-4">
          SAVE YOUR CREDENTIALS NOW!
        </h2>

        <p className="text-ui-dark text-center mb-2">
          You can take a screenshot, photo or email them to yourself.
        </p>
        <p className="text-danger text-center font-semibold mb-6">
          If you lose your password you will lose your progress.
        </p>

        <div className="bg-ui-lighter rounded-lg p-4 mb-4">
          <p className="text-sm font-semibold text-ui-dark/70">TEAM NAME:</p>
          <p className="text-xl font-mono text-ui-dark break-all mb-3">
            {teamName}
          </p>

          <p className="text-sm font-semibold text-ui-dark/70">PASSWORD:</p>
          <div className="flex items-center gap-2">
            <p className="text-xl font-mono text-ui-dark break-all flex-1">
              {revealed ? password : "•".repeat(Math.max(password.length, 6))}
            </p>
            <button
              type="button"
              onClick={() => setRevealed((v) => !v)}
              className="px-3 py-1 text-sm font-medium text-white bg-primary hover:bg-primary-hover rounded transition-colors"
            >
              {revealed ? "HIDE" : "REVEAL"}
            </button>
          </div>
        </div>

        <button
          type="button"
          onClick={onDismiss}
          className="w-full py-3 px-4 text-lg font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors"
        >
          {dismissLabel}
        </button>
      </div>
    </div>
  );
}

export default CredentialsModal;
