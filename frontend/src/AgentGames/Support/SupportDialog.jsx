import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import { closeSupportDialog } from '../../slices/supportSlice';
import { authFetch } from '../../utils/authFetch';
import ImageDropzone from './ImageDropzone';

const CATEGORIES = [
  { value: 'bug', label: 'Report a bug' },
  { value: 'support', label: 'Request support' },
  { value: 'feedback', label: 'Submit feedback' },
];

const MAX_SUBJECT = 200;
const MAX_DESCRIPTION = 5000;

function SupportDialog() {
  const dispatch = useDispatch();
  const isOpen = useSelector((state) => state.support.isDialogOpen);
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);

  const [category, setCategory] = useState('bug');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [files, setFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setCategory('bug');
      setSubject('');
      setDescription('');
      setFiles([]);
      setSubmitting(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleFilesChange = (next, { rejected, truncated }) => {
    setFiles(next);
    if (rejected && rejected.length > 0) {
      rejected.forEach((r) => toast.error(`${r.file.name}: ${r.reason}`));
    }
    if (truncated) {
      toast.info('Only the first 3 images were kept.');
    }
  };

  const handleClose = () => {
    if (submitting) return;
    dispatch(closeSupportDialog());
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmedSubject = subject.trim();
    const trimmedDescription = description.trim();
    if (!trimmedSubject) {
      toast.error('Please enter a subject.');
      return;
    }
    if (!trimmedDescription) {
      toast.error('Please enter a description.');
      return;
    }

    const formData = new FormData();
    formData.append('category', category);
    formData.append('subject', trimmedSubject);
    formData.append('description', trimmedDescription);
    files.forEach((file) => formData.append('files', file));

    setSubmitting(true);
    try {
      const response = await authFetch(`${apiUrl}/support/create-ticket`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
        body: formData,
      });
      const data = await response.json();
      if (data.status === 'success') {
        toast.success('Thanks — your message has been sent to the team.');
        dispatch(closeSupportDialog());
      } else {
        toast.error(data.message || 'Failed to submit ticket.');
      }
    } catch (err) {
      console.error('Support submit failed:', err);
      toast.error('Could not submit support ticket.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 px-4"
      role="dialog"
      aria-modal="true"
      onClick={handleClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-ui-light">
          <h2 className="text-xl font-semibold text-ui-dark">Contact support</h2>
          <button
            type="button"
            onClick={handleClose}
            disabled={submitting}
            className="text-ui hover:text-ui-dark text-2xl leading-none"
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-ui-dark mb-2">
              What would you like to do?
            </label>
            <div className="space-y-2">
              {CATEGORIES.map((opt) => (
                <label
                  key={opt.value}
                  className={`flex items-center px-3 py-2 border rounded-lg cursor-pointer ${
                    category === opt.value
                      ? 'border-primary bg-ui-lighter'
                      : 'border-ui-light hover:bg-ui-lighter/50'
                  }`}
                >
                  <input
                    type="radio"
                    name="category"
                    value={opt.value}
                    checked={category === opt.value}
                    onChange={(e) => setCategory(e.target.value)}
                    className="mr-2"
                    disabled={submitting}
                  />
                  <span className="text-ui-dark">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="support-subject" className="block text-sm font-medium text-ui-dark mb-1">
              Subject
            </label>
            <input
              id="support-subject"
              type="text"
              value={subject}
              maxLength={MAX_SUBJECT}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full p-2 border border-ui-light rounded-lg"
              placeholder="Short summary"
              disabled={submitting}
              required
            />
          </div>

          <div>
            <label htmlFor="support-description" className="block text-sm font-medium text-ui-dark mb-1">
              Description
            </label>
            <textarea
              id="support-description"
              value={description}
              maxLength={MAX_DESCRIPTION}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full p-2 border border-ui-light rounded-lg min-h-[120px]"
              placeholder="Details, steps, context…"
              disabled={submitting}
              required
            />
            <div className="text-xs text-ui text-right mt-1">
              {description.length}/{MAX_DESCRIPTION}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-ui-dark mb-1">
              Attachments (optional)
            </label>
            <ImageDropzone files={files} onChange={handleFilesChange} disabled={submitting} />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={submitting}
              className="px-4 py-2 border border-ui-light rounded-lg text-ui-dark hover:bg-ui-lighter disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg disabled:opacity-50"
            >
              {submitting ? 'Sending…' : 'Send'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default SupportDialog;
