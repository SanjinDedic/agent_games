import { toast } from "react-toastify";

const ERROR_AUTOCLOSE_MS = 60000;

const originalError = toast.error.bind(toast);
toast.error = (content, options = {}) =>
  originalError(content, { autoClose: ERROR_AUTOCLOSE_MS, ...options });
