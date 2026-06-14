// frontend/src/components/FileUploadZone.jsx

/**
 * Drag-and-drop file upload zone for resumes and cover letters.
 *
 * Props:
 *   label      — e.g. "Resume" or "Cover Letter"
 *   currentPath — current stored path (shows download link if set)
 *   onUploaded  — called with { filename, path } after a successful upload
 *   appId       — application ID (used to link the uploaded file)
 *
 * Upload flow (per CLAUDE.md):
 *   1. User drops/selects file → client-side validateFile()
 *   2. useUploadFile() → POST /api/files/upload → { filename, path }
 *   3. useUpdateApplication() → PATCH /api/applications/{id} with path
 */

import { useRef, useState } from 'react';
import { useUpdateApplication, useUploadFile } from '../hooks/useApplications';
import { openFileDownload, validateFile } from '../services/fileService';

export default function FileUploadZone({ label, currentPath, onUploaded, appId, field }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState(null);

  const uploadMutation  = useUploadFile();
  const updateMutation  = useUpdateApplication();

  const isPending = uploadMutation.isPending || updateMutation.isPending;
  const mutationError = uploadMutation.error?.userMessage || updateMutation.error?.userMessage;

  const processFile = async (file) => {
    setValidationError(null);

    // Client-side validation first (instant feedback)
    const { valid, error } = validateFile(file);
    if (!valid) {
      setValidationError(error);
      return;
    }

    try {
      // 1. Upload file
      const result = await uploadMutation.mutateAsync(file);
      // 2. Link to application
      await updateMutation.mutateAsync({
        id: appId,
        body: { [field]: result.path },
      });
      onUploaded?.(result);
    } catch {
      // Errors surfaced via mutationError above
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) await processFile(file);
  };

  const handleInputChange = async (e) => {
    const file = e.target.files?.[0];
    if (file) await processFile(file);
    e.target.value = ''; // reset so same file can be re-uploaded
  };

  // Extract just the filename from the stored path for display.
  // currentPath is now `<user_id>/<random>.<ext>`; we only show the trailing segment.
  const storedFilename = currentPath
    ? currentPath.split('/').pop()
    : null;

  const handleDownload = async (e) => {
    e.stopPropagation();
    try {
      await openFileDownload(currentPath);
    } catch (err) {
      setValidationError(err.userMessage || 'Failed to open download.');
    }
  };

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-slate-400">{label}</p>

      {/* Drop zone */}
      <div
        onDragEnter={() => setIsDragging(true)}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !isPending && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && !isPending && inputRef.current?.click()}
        aria-label={`Upload ${label} — PDF or DOCX, max 5 MB`}
        className={`relative flex flex-col items-center justify-center gap-2 p-6
                    rounded-xl border-2 border-dashed cursor-pointer
                    transition-all duration-200 text-center
                    ${isDragging
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-700 bg-slate-800/50 hover:border-slate-500 hover:bg-slate-800'}
                    ${isPending ? 'cursor-wait opacity-70' : ''}`}
      >
        {isPending ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent
                            rounded-full animate-spin" />
            <p className="text-xs text-slate-400">Uploading…</p>
          </div>
        ) : (
          <>
            <div className="text-2xl">{isDragging ? '📂' : '📎'}</div>
            <div>
              <p className="text-sm font-medium text-slate-300">
                {isDragging ? 'Drop to upload' : 'Drop file or click to browse'}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">PDF or DOCX · max 5 MB</p>
            </div>
          </>
        )}

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleInputChange}
          className="sr-only"
          tabIndex={-1}
          aria-hidden="true"
        />
      </div>

      {/* Current file */}
      {storedFilename && (
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-800
                        border border-slate-700 rounded-lg">
          <span className="text-base">📄</span>
          <span className="text-xs text-slate-400 flex-1 truncate">{storedFilename}</span>
          <button
            type="button"
            onClick={handleDownload}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors shrink-0"
          >
            Download ↓
          </button>
        </div>
      )}

      {/* Errors */}
      {(validationError || mutationError) && (
        <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20
                      rounded-lg px-3 py-2">
          {validationError || mutationError}
        </p>
      )}
    </div>
  );
}
