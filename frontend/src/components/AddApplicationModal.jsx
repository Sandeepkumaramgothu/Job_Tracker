// frontend/src/components/AddApplicationModal.jsx

/**
 * Modal for creating a new job application.
 *
 * Flow (top to bottom):
 *   1. Paste the JD into the textarea and click "Extract with AI". The
 *      backend calls the user's OpenAI key and fills in the form fields.
 *   2. Review / edit any field manually.
 *   3. Optionally drop a resume + cover-letter PDF.
 *   4. Click Save — we create the application, then upload each file and
 *      PATCH the resulting paths onto the new app.
 */

import { useRef, useState } from 'react';
import { useCreateApplication, useUpdateApplication, useUploadFile } from '../hooks/useApplications';
import { extractJobDescription } from '../services/aiService';
import { validateFile } from '../services/fileService';

const INITIAL = {
  job_title: '',
  company: '',
  date_applied: new Date().toISOString().split('T')[0],
  source: '',
  location: '',
  salary_range: '',
  job_description: '',
  notes: '',
  status: 'applied',
};

const SOURCE_OPTIONS = ['LinkedIn', 'Indeed', 'Glassdoor', 'Company site', 'Referral', 'Other'];
const STATUS_OPTIONS = [
  { value: 'applied',   label: 'Applied' },
  { value: 'interview', label: 'Interview' },
  { value: 'followup',  label: 'Follow-up' },
  { value: 'offer',     label: 'Offer' },
  { value: 'rejected',  label: 'Rejected' },
];

// ---------------------------------------------------------------------------
// Inline file-picker chip. Lighter than the full FileUploadZone — designed
// to live inside a busy modal next to other form fields.
// ---------------------------------------------------------------------------
function FilePicker({ label, file, onChange, id }) {
  const inputRef = useRef(null);
  return (
    <div>
      <p className="block text-xs font-semibold text-slate-400 mb-1.5">{label}</p>
      <button
        type="button"
        id={id}
        onClick={() => inputRef.current?.click()}
        className="w-full flex items-center gap-2 px-3.5 py-2.5 bg-slate-800
                   border border-dashed border-slate-700 rounded-xl text-sm
                   text-slate-300 hover:border-slate-500 hover:bg-slate-800/80
                   transition-colors text-left"
      >
        <span className="text-base shrink-0">📎</span>
        <span className="truncate flex-1">
          {file ? file.name : 'Choose PDF or DOCX…'}
        </span>
        {file && (
          <span
            role="button"
            tabIndex={0}
            aria-label="Clear selection"
            className="text-xs text-slate-500 hover:text-red-300 shrink-0"
            onClick={(e) => { e.stopPropagation(); onChange(null); }}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); onChange(null); } }}
          >
            ✕
          </span>
        )}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        className="sr-only"
      />
    </div>
  );
}

export default function AddApplicationModal({ onClose, onCreated }) {
  const [form, setForm] = useState(INITIAL);
  const [resumeFile, setResumeFile] = useState(null);
  const [coverFile, setCoverFile] = useState(null);
  const [error, setError] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [extractInfo, setExtractInfo] = useState(null);

  const createMutation = useCreateApplication();
  const updateMutation = useUpdateApplication();
  const uploadMutation = useUploadFile();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleExtract = async () => {
    setError(null);
    setExtractInfo(null);
    if (form.job_description.trim().length < 20) {
      return setError('Paste at least a paragraph of the job description first.');
    }
    setExtracting(true);
    try {
      const parsed = await extractJobDescription(form.job_description);
      // Fill any field that the AI returned non-null AND the user hasn't
      // already typed into. We don't clobber manual edits.
      setForm((prev) => ({
        ...prev,
        job_title:    prev.job_title    || parsed.job_title    || '',
        company:      prev.company      || parsed.company      || '',
        location:     prev.location     || parsed.location     || '',
        salary_range: prev.salary_range || parsed.salary_range || '',
        source:       prev.source       || parsed.source       || '',
        notes:        prev.notes        || parsed.notes        || '',
      }));
      const filled = ['job_title', 'company', 'location', 'salary_range', 'source', 'notes']
        .filter((k) => parsed[k]).length;
      setExtractInfo(`Filled ${filled} field${filled === 1 ? '' : 's'} from the JD.`);
    } catch (err) {
      setError(err.userMessage || 'AI extraction failed.');
    } finally {
      setExtracting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!form.job_title.trim()) return setError('Job title is required.');
    if (!form.company.trim())   return setError('Company is required.');
    if (!form.date_applied)     return setError('Date applied is required.');

    // Client-side file validation before any network calls
    for (const f of [resumeFile, coverFile]) {
      if (f) {
        const v = validateFile(f);
        if (!v.valid) return setError(v.error);
      }
    }

    try {
      const created = await createMutation.mutateAsync({
        ...form,
        job_title:       form.job_title.trim(),
        company:         form.company.trim(),
        source:          form.source           || undefined,
        location:        form.location         || undefined,
        salary_range:    form.salary_range     || undefined,
        job_description: form.job_description  || undefined,
        notes:           form.notes            || undefined,
      });

      // Upload files (sequentially — clearer error attribution) then PATCH
      const pathUpdate = {};
      if (resumeFile) {
        const r = await uploadMutation.mutateAsync(resumeFile);
        pathUpdate.resume_path = r.path;
      }
      if (coverFile) {
        const c = await uploadMutation.mutateAsync(coverFile);
        pathUpdate.cover_path = c.path;
      }
      if (Object.keys(pathUpdate).length > 0) {
        await updateMutation.mutateAsync({ id: created.id, body: pathUpdate });
      }

      onCreated?.(created);
      onClose();
    } catch (err) {
      setError(err.userMessage || 'Failed to create application.');
    }
  };

  const isSaving =
    createMutation.isPending || updateMutation.isPending || uploadMutation.isPending;

  // Field helper for repetitive plain-text inputs
  const field = (label, name, type = 'text', opts = {}) => (
    <div className={opts.colSpan === 2 ? 'col-span-2' : ''}>
      <label htmlFor={`add-${name}`} className="block text-xs font-semibold text-slate-400 mb-1.5">
        {label}{opts.required && <span className="text-red-400 ml-1">*</span>}
      </label>
      <input
        id={`add-${name}`}
        name={name}
        type={type}
        value={form[name]}
        onChange={handleChange}
        placeholder={opts.placeholder || ''}
        required={opts.required}
        className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                   text-sm text-slate-100 placeholder-slate-500
                   focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                   transition-colors"
      />
    </div>
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4
                 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl
                   w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between
                        px-6 py-4 bg-slate-900 border-b border-slate-700/50">
          <h2 className="text-lg font-bold text-white">New Application</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300
                       hover:bg-slate-800 transition-colors"
            aria-label="Close modal"
          >
            <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* AI extract */}
          <div className="space-y-2 p-4 bg-blue-500/5 border border-blue-500/20 rounded-2xl">
            <div className="flex items-center justify-between">
              <label htmlFor="add-job_description" className="text-xs font-semibold text-blue-200">
                ✨ Paste the job description and let AI fill the form
              </label>
              <button
                id="add-extract-btn"
                type="button"
                onClick={handleExtract}
                disabled={extracting}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50
                           text-white text-xs font-semibold rounded-lg transition-colors
                           disabled:cursor-not-allowed"
              >
                {extracting ? 'Extracting…' : 'Extract with AI'}
              </button>
            </div>
            <textarea
              id="add-job_description"
              name="job_description"
              value={form.job_description}
              onChange={handleChange}
              rows={5}
              placeholder="Paste the full job description here…"
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                         text-sm text-slate-100 placeholder-slate-500 resize-y
                         focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                         transition-colors"
            />
            {extractInfo && (
              <p className="text-xs text-emerald-300">{extractInfo}</p>
            )}
          </div>

          {/* Core fields */}
          <div className="grid grid-cols-2 gap-4">
            {field('Job Title', 'job_title', 'text', { required: true, placeholder: 'Software Engineer' })}
            {field('Company', 'company', 'text', { required: true, placeholder: 'Acme Corp' })}
            {field('Date Applied', 'date_applied', 'date', { required: true })}

            <div>
              <label htmlFor="add-source" className="block text-xs font-semibold text-slate-400 mb-1.5">
                Source
              </label>
              <select
                id="add-source"
                name="source"
                value={form.source}
                onChange={handleChange}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                           text-sm text-slate-100 focus:outline-none focus:border-blue-500
                           focus:ring-1 focus:ring-blue-500 transition-colors cursor-pointer"
              >
                <option value="">Select source…</option>
                {SOURCE_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            {field('Location', 'location', 'text', { placeholder: 'Remote / San Francisco, CA' })}
            {field('Salary Range', 'salary_range', 'text', { placeholder: '$120k – $150k' })}

            <div>
              <label htmlFor="add-status" className="block text-xs font-semibold text-slate-400 mb-1.5">
                Initial Status
              </label>
              <select
                id="add-status"
                name="status"
                value={form.status}
                onChange={handleChange}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                           text-sm text-slate-100 focus:outline-none focus:border-blue-500
                           focus:ring-1 focus:ring-blue-500 transition-colors cursor-pointer"
              >
                {STATUS_OPTIONS.filter((s) => s.value !== 'interview').map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* File uploads */}
          <div className="grid grid-cols-2 gap-4">
            <FilePicker
              id="add-resume"
              label="Resume (optional)"
              file={resumeFile}
              onChange={setResumeFile}
            />
            <FilePicker
              id="add-cover"
              label="Cover Letter (optional)"
              file={coverFile}
              onChange={setCoverFile}
            />
          </div>

          {/* Notes */}
          <div>
            <label htmlFor="add-notes" className="block text-xs font-semibold text-slate-400 mb-1.5">
              Notes
            </label>
            <textarea
              id="add-notes"
              name="notes"
              value={form.notes}
              onChange={handleChange}
              rows={2}
              placeholder="Recruiter contact, referral info, talking points…"
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                         text-sm text-slate-100 placeholder-slate-500 resize-y
                         focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                         transition-colors"
            />
          </div>

          {error && (
            <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl p-3">
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 bg-slate-800 hover:bg-slate-700
                         text-slate-300 text-sm font-semibold rounded-xl
                         border border-slate-700 transition-colors"
            >
              Cancel
            </button>
            <button
              id="add-application-submit"
              type="submit"
              disabled={isSaving}
              className="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-500
                         text-white text-sm font-semibold rounded-xl transition-colors
                         shadow-lg shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? 'Saving…' : 'Add Application'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
