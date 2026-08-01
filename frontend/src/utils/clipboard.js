// src/utils/clipboard.js
import { toast } from 'react-toastify';

// Copy text and confirm with a toast. The write is fire-and-forget: it
// only rejects in insecure contexts, where a console line is all we owe.
export function copyToClipboard(text, message = 'Copied to clipboard!') {
  navigator.clipboard.writeText(text).catch(console.error);
  toast.success(message);
}
