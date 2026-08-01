// src/utils/urls.js

// Absolute URLs for the two token links teachers hand to students.
export const joinUrl = (token) => `${window.location.origin}/join/${token}`;
export const resetUrl = (token) => `${window.location.origin}/reset/${token}`;
