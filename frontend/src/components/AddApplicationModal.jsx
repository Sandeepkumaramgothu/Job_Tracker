// frontend/src/components/AddApplicationModal.jsx

/**
 * Modal for creating a new job application.
 * Uses controlled inputs with useState per CLAUDE.md rules.
 * Calls useCreateApplication() hook on submit.
 */

import { useState } from 'react';
import { useCreateApplication } from '../hooks/useApplications';

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

export default function AddApplicationModal({ onClose, onCreated }) {
  const [form, setForm] = useState(INITIAL);
  const [error, setError] = useState(null);
  const { mutateAsync, isPending } = useCreateApplication();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!form.job_title.trim()) return setError('Job title is required.');
    if (!form.company.trim())   return setError('Company is required.');
    if (!form.date_applied)     return setError('Date applied is required.');
    try {
      const created = await mutateAsync({
        ...form,
        job_title:       form.job_title.trim(),
        company:         form.company.trim(),
        source:          form.source      || undefined,
        location:        form.location    || undefined,
        salary_range:    form.salary_range || undefined,
        job_description: form.job_description || undefined,
        notes:           form.notes       || undefined,
      });
      onCreated?.(created);
      onClose();
    } catch (err) {
      setError(err.userMessage || 'Failed to create application.');
    }
  };

  // Field helper
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

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            {field('Job Title', 'job_title', 'text', { required: true, placeholder: 'Software Engineer' })}
            {field('Company', 'company', 'text', { required: true, placeholder: 'Acme Corp' })}
            {field('Date Applied', 'date_applied', 'date', { required: true })}

            {/* Source select */}
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

            {/* Status select */}
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
                {STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
          </div>

          {/* Job description */}
          <div>
            <label htmlFor="add-job_description" className="block text-xs font-semibold text-slate-400 mb-1.5">
              Job Description
            </label>
            <textarea
              id="add-job_description"
              name="job_description"
              value={form.job_description}
              onChange={handleChange}
              rows={4}
              placeholder="Paste the job description here…"
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                         text-sm text-slate-100 placeholder-slate-500 resize-y
                         focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                         transition-colors"
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

          {/* Error */}
          {error && (
            <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl p-3">
              {error}
            </div>
          )}

          {/* Actions */}
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
              disabled={isPending}
              className="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-500
                         text-white text-sm font-semibold rounded-xl transition-colors
                         shadow-lg shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending ? 'Saving…' : 'Add Application'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
