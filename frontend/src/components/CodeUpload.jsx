/**
 * CodeUpload – File upload for code analysis.
 * Backend: POST /analyze/code with FormData { file }
 */

import React, { useRef, useState } from 'react';

function CodeUpload({ onUpload, loading, disabled }) {
  const inputRef = useRef(null);
  const [invalidFile, setInvalidFile] = useState(false);

  function isValidFile(file) {
    const name = (file?.name || '').toLowerCase();
    return name.endsWith('.py') || name.endsWith('.c');
  }

  function handleChange(e) {
    setInvalidFile(false);
    const file = e.target.files?.[0];
    if (!file) {
      e.target.value = '';
      return;
    }
    if (isValidFile(file)) {
      onUpload(file);
    } else {
      setInvalidFile(true);
    }
    e.target.value = '';
  }

  function handleDrop(e) {
    e.preventDefault();
    setInvalidFile(false);
    const file = e.dataTransfer?.files?.[0];
    if (file && isValidFile(file)) {
      onUpload(file);
    } else if (file) {
      setInvalidFile(true);
    }
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  return (
    <div
      className="code-upload"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".py,.c"
        onChange={handleChange}
        disabled={disabled}
        aria-label="Upload Python or C file"
      />
      <button
        type="button"
        onClick={() => { setInvalidFile(false); inputRef.current?.click(); }}
        disabled={disabled}
        className="upload-btn"
      >
        {loading ? (
          <>
            <span className="spinner small" aria-hidden="true" />
            Analyzing…
          </>
        ) : (
          'Choose .py or .c file or drop here'
        )}
      </button>
      {invalidFile && (
        <p className="upload-error" role="alert">Only .py and .c files are accepted.</p>
      )}
      <p className="upload-hint">Python (.py) or C (.c) files. UTF-8 encoded.</p>
    </div>
  );
}

export default CodeUpload;
