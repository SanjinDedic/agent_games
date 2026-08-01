// src/AgentGames/Shared/ResetLinkModal.jsx
import React from 'react';
import { useTerms } from './terminology';
import { copyToClipboard } from '../../utils/clipboard';
import { resetUrl } from '../../utils/urls';

/**
 * Share-this-reset-link modal shown after generating a password reset
 * link for a team. Builds the /reset/ URL from the token so the path
 * lives in one place. Renders nothing until resetToken is set, so
 * callers can render it unconditionally.
 */
function ResetLinkModal({ teamName, resetToken, onClose }) {
  const T = useTerms();
  if (!resetToken) return null;
  const url = resetUrl(resetToken);
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-lg p-6 w-full max-w-lg space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-ui-dark">
          {`Password reset link for ${teamName}`}
        </h2>
        <p className="text-ui-dark/70">
          {`Share this link with the ${T.team}. It opens a page showing their name where they set a new password and are logged straight back into their account — all their work is kept. The link works once and expires in 48 hours.`}
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            readOnly
            onFocus={(e) => e.target.select()}
            className="flex-1 p-3 border border-ui-light rounded-lg text-sm bg-ui-lighter"
          />
          <button
            onClick={() => copyToClipboard(url, 'Password reset link copied to clipboard!')}
            className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg font-medium"
            title="Copy to clipboard"
          >
            Copy
          </button>
        </div>
        <button
          onClick={onClose}
          className="w-full py-2 bg-ui-lighter hover:bg-ui-light text-ui-dark rounded-lg font-medium"
        >
          Close
        </button>
      </div>
    </div>
  );
}

export default ResetLinkModal;
