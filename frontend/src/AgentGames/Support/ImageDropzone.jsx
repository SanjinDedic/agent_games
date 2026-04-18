import React, { useRef } from 'react';

const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
const MAX_BYTES = 5 * 1024 * 1024;
const MAX_COUNT = 3;

function ImageDropzone({ files, onChange, disabled }) {
  const inputRef = useRef(null);

  const addFiles = (incoming) => {
    const list = Array.from(incoming || []);
    const accepted = [];
    const rejected = [];
    for (const file of list) {
      if (!ALLOWED_TYPES.includes(file.type)) {
        rejected.push({ file, reason: 'Only PNG, JPEG, or WebP images are allowed.' });
        continue;
      }
      if (file.size > MAX_BYTES) {
        rejected.push({ file, reason: 'Each image must be 5 MB or smaller.' });
        continue;
      }
      accepted.push(file);
    }
    const next = [...files, ...accepted].slice(0, MAX_COUNT);
    const truncated = files.length + accepted.length > MAX_COUNT;
    onChange(next, {
      rejected,
      truncated,
    });
  };

  const handleRemove = (idx) => {
    const next = files.slice();
    next.splice(idx, 1);
    onChange(next, { rejected: [], truncated: false });
  };

  const handleFileInputChange = (e) => {
    addFiles(e.target.files);
    e.target.value = '';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (disabled) return;
    addFiles(e.dataTransfer.files);
  };

  return (
    <div>
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
          disabled
            ? 'border-ui-light bg-ui-lighter/50 cursor-not-allowed'
            : 'border-ui-light hover:border-primary hover:bg-ui-lighter'
        }`}
        onClick={() => !disabled && inputRef.current?.click()}
      >
        <p className="text-sm text-ui-dark">
          Drag images here or <span className="text-primary underline">choose files</span>
        </p>
        <p className="text-xs text-ui mt-1">
          PNG, JPEG, or WebP · up to {MAX_COUNT} images · 5 MB each
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_TYPES.join(',')}
          multiple
          hidden
          disabled={disabled}
          onChange={handleFileInputChange}
        />
      </div>

      {files.length > 0 && (
        <ul className="mt-3 space-y-2">
          {files.map((file, idx) => (
            <li
              key={`${file.name}-${idx}`}
              className="flex items-center justify-between bg-ui-lighter rounded px-3 py-2"
            >
              <span className="text-sm text-ui-dark truncate mr-3">
                {file.name}
                <span className="text-xs text-ui ml-2">
                  {(file.size / 1024).toFixed(1)} KB
                </span>
              </span>
              <button
                type="button"
                onClick={() => handleRemove(idx)}
                disabled={disabled}
                className="text-xs text-danger hover:text-danger-hover disabled:opacity-50"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default ImageDropzone;
