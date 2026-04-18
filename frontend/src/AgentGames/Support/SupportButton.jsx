import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { openSupportDialog } from '../../slices/supportSlice';
import SupportDialog from './SupportDialog';

const ALLOWED_ROLES = ['student', 'institution'];

function SupportButton() {
  const dispatch = useDispatch();
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  const role = useSelector((state) => state.auth.currentUser?.role);

  if (!isAuthenticated || !ALLOWED_ROLES.includes(role)) {
    return null;
  }

  return (
    <>
      <button
        onClick={() => dispatch(openSupportDialog())}
        className="fixed bottom-4 right-16 h-10 px-4 bg-success hover:bg-success-hover text-white rounded-full shadow-lg flex items-center justify-center gap-2 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-success-light z-40"
        title="Contact support"
        aria-label="Contact support"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="w-4 h-4"
        >
          <path d="M4 4h16a2 2 0 012 2v10a2 2 0 01-2 2h-9l-5 4v-4H4a2 2 0 01-2-2V6a2 2 0 012-2z" />
        </svg>
        <span className="text-sm font-medium">Support</span>
      </button>
      <SupportDialog />
    </>
  );
}

export default SupportButton;
