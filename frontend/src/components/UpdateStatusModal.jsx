// frontend/src/components/UpdateStatusModal.jsx

/**
 * Modal for updating application status and appending a timeline event.
 * When status = 'interview', shows interview-specific fields.
 * Controlled inputs with useState throughout.
 */

import { useState } from 'react';
import { useUpdateApplication } from '../hooks/useApplications';

const STATUS_OPTIONS = [
  { value: 'applied',   label: 'Applied',    emoji: '📝' },
  { value: 'interview', label: 'Interview',  emoji: '🎙️' },
  { value: 'followup',  label: 'Follow-up',  emoji: '📧' },
  { value: 'offer',     label: 'Offer',      emoji: '🎉' },
  { value: 'rejected',  label: 'Rejected',   emoji: '❌' },
];

const INTERVIEW_TYPES = ['Phone', 'Technical', 'Panel', 'Final', 'Other'];

export default function UpdateStatusModal({ app, onClose }) {
  const today = new Date().toISOString().split('T')[0];

  const [form, setForm] = useState({
    status: app.status,
    event_date: today,
    note: '',
    interview_date: '',
    interview_type: '',
    interviewer: '',
  });
  const [error, setError] = useState(null);
  const { mutateAsync, isPending } = useUpdateApplication();

  const isInterview = form.status === 'interview';

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (isInterview && !form.interview_date) {
      return setError('Interview date is required when status is Interview.');
    }

    const timelineEvent = {
      event_date: form.event_date,
      status: form.status,
      note: form.note || undefined,
      ...(isInterview && {
        interview_date: form.interview_date,
        interview_type: form.interview_type || undefined,
        interviewer:    form.interviewer    || undefined,
      }),
    };

    try {
      await mutateAsync({
        id: app.id,
        body: {
          status: form.status,
          timeline_event: timelineEvent,
        },
      });
      onClose();
    } catch (err) {
      setError(err.userMessage || 'Failed to update status.');
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4
                 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl
                   w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4
                        border-b border-slate-700/50">
          <div>
            <h2 className="text-lg font-bold text-white">Update Status</h2>
            <p className="text-xs text-slate-400 mt-0.5 truncate">
              {app.job_title} · {app.company}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300
                       hover:bg-slate-800 transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">

          {/* Status picker */}
          <div>
            <p className="text-xs font-semibold text-slate-400 mb-2">New Status</p>
            <div className="grid grid-cols-5 gap-2">
              {STATUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  id={`status-${opt.value}`}
                  onClick={() => setForm((p) => ({ ...p, status: opt.value }))}
                  className={`flex flex-col items-center gap-1 p-2.5 rounded-xl border text-xs
                              font-semibold transition-all duration-150
                              ${form.status === opt.value
                                ? 'bg-blue-600/20 border-blue-500 text-blue-300'
                                : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500'}`}
                >
                  <span className="text-base">{opt.emoji}</span>
                  <span>{opt.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Event date */}
          <div>
            <label htmlFor="update-event_date" className="block text-xs font-semibold text-slate-400 mb-1.5">
              Date of Event <span className="text-red-400">*</span>
            </label>
            <input
              id="update-event_date"
              name="event_date"
              type="date"
              value={form.event_date}
              onChange={handleChange}
              required
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                         text-sm text-slate-100 focus:outline-none focus:border-blue-500
                         focus:ring-1 focus:ring-blue-500 transition-colors"
            />
          </div>

          {/* Interview-specific fields */}
          {isInterview && (
            <div className="space-y-4 p-4 bg-violet-500/5 border border-violet-500/20 rounded-xl">
              <p className="text-xs font-semibold text-violet-300">Interview Details</p>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="update-interview_date" className="block text-xs font-semibold text-slate-400 mb-1.5">
                    Interview Date <span className="text-red-400">*</span>
                  </label>
                  <input
                    id="update-interview_date"
                    name="interview_date"
                    type="date"
                    value={form.interview_date}
                    onChange={handleChange}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                               text-sm text-slate-100 focus:outline-none focus:border-blue-500
                               focus:ring-1 focus:ring-blue-500 transition-colors"
                  />
                </div>

                <div>
                  <label htmlFor="update-interview_type" className="block text-xs font-semibold text-slate-400 mb-1.5">
                    Interview Type
                  </label>
                  <select
                    id="update-interview_type"
                    name="interview_type"
                    value={form.interview_type}
                    onChange={handleChange}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                               text-sm text-slate-100 focus:outline-none focus:border-blue-500
                               focus:ring-1 focus:ring-blue-500 transition-colors cursor-pointer"
                  >
                    <option value="">Select type…</option>
                    {INTERVIEW_TYPES.map((t) => (
                      <option key={t} value={t.toLowerCase()}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="update-interviewer" className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Interviewer
                </label>
                <input
                  id="update-interviewer"
                  name="interviewer"
                  type="text"
                  value={form.interviewer}
                  onChange={handleChange}
                  placeholder="Name, title, or contact info"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                             text-sm text-slate-100 placeholder-slate-500
                             focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                             transition-colors"
                />
              </div>
            </div>
          )}

          {/* Note */}
          <div>
            <label htmlFor="update-note" className="block text-xs font-semibold text-slate-400 mb-1.5">
              Note
            </label>
            <textarea
              id="update-note"
              name="note"
              value={form.note}
              onChange={handleChange}
              rows={2}
              placeholder="What happened? Recruiter feedback, outcome…"
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                         text-sm text-slate-100 placeholder-slate-500 resize-none
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
              id="update-status-submit"
              type="submit"
              disabled={isPending}
              className="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-500
                         text-white text-sm font-semibold rounded-xl transition-colors
                         shadow-lg shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending ? 'Saving…' : 'Save Update'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
