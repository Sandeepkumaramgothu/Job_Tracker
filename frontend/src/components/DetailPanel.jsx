// frontend/src/components/DetailPanel.jsx

/**
 * Slide-in detail panel for a single application.
 * Shows: header info, file upload zones, full job description/notes,
 * and the complete timeline.
 * Provides "Update Status" button which opens UpdateStatusModal.
 *
 * Props:
 *   appId   — UUID of the application to show
 *   onClose — callback to close the panel
 */

import { useState } from 'react';
import { useApplication } from '../hooks/useApplications';
import Timeline from './Timeline';
import UpdateStatusModal from './UpdateStatusModal';
import FileUploadZone from './FileUploadZone';

const STATUS_CONFIG = {
  applied:   { label: 'Applied',   classes: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
  interview: { label: 'Interview', classes: 'bg-violet-500/20 text-violet-300 border-violet-500/30' },
  followup:  { label: 'Follow-up', classes: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
  offer:     { label: 'Offer',     classes: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
  rejected:  { label: 'Rejected',  classes: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

function formatDate(d) {
  if (!d) return '—';
  return new Date(d + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

function InfoRow({ label, value }) {
  if (!value) return null;
  return (
    <div>
      <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-0.5">{label}</dt>
      <dd className="text-sm text-slate-300">{value}</dd>
    </div>
  );
}

export default function DetailPanel({ appId, onClose }) {
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const { data: app, isLoading, error } = useApplication(appId);

  const status = app ? (STATUS_CONFIG[app.status] ?? { label: app.status, classes: 'bg-slate-700 text-slate-300 border-slate-600' }) : null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <aside
        className="fixed right-0 top-0 bottom-0 z-40 w-full max-w-lg
                   bg-slate-900 border-l border-slate-700/50 shadow-2xl
                   flex flex-col overflow-hidden
                   animate-[slideIn_0.22s_ease-out]"
        role="dialog"
        aria-modal="true"
        aria-label="Application detail"
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-6 pb-4
                        border-b border-slate-700/50">
          {isLoading ? (
            <div className="animate-pulse space-y-2">
              <div className="h-5 bg-slate-700 rounded w-48" />
              <div className="h-4 bg-slate-700 rounded w-32" />
            </div>
          ) : error ? (
            <p className="text-red-400 text-sm">{error.userMessage}</p>
          ) : app ? (
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-bold text-white leading-snug">{app.job_title}</h2>
              <p className="text-slate-400 text-sm mt-0.5">{app.company}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${status.classes}`}>
                  {status.label}
                </span>
                {app.location && (
                  <span className="text-xs text-slate-500">{app.location}</span>
                )}
              </div>
            </div>
          ) : null}

          <button
            onClick={onClose}
            className="ml-4 shrink-0 p-1.5 rounded-lg text-slate-500 hover:text-slate-300
                       hover:bg-slate-800 transition-colors"
            aria-label="Close panel"
          >
            <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd" />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {isLoading && (
            <div className="animate-pulse space-y-3">
              {[80, 60, 100, 80].map((w, i) => (
                <div key={i} className={`h-4 bg-slate-800 rounded w-[${w}%]`} />
              ))}
            </div>
          )}

          {app && (
            <>
              {/* Meta info */}
              <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
                <InfoRow label="Date Applied" value={formatDate(app.date_applied)} />
                <InfoRow label="Source"       value={app.source} />
                <InfoRow label="Salary Range" value={app.salary_range} />
                <InfoRow label="Location"     value={app.location} />
              </dl>

              {/* Files */}
              <div className="space-y-3">
                <FileUploadZone
                  label="Resume"
                  currentPath={app.resume_path}
                  appId={app.id}
                  field="resume_path"
                />
                <FileUploadZone
                  label="Cover Letter"
                  currentPath={app.cover_path}
                  appId={app.id}
                  field="cover_path"
                />
              </div>

              {/* Job description */}
              {app.job_description && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                    Job Description
                  </h3>
                  <div className="text-sm text-slate-400 leading-relaxed whitespace-pre-wrap
                                  bg-slate-800/60 border border-slate-700/50 rounded-xl p-4
                                  max-h-48 overflow-y-auto">
                    {app.job_description}
                  </div>
                </div>
              )}

              {/* Notes */}
              {app.notes && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                    Notes
                  </h3>
                  <div className="text-sm text-slate-400 leading-relaxed whitespace-pre-wrap
                                  bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
                    {app.notes}
                  </div>
                </div>
              )}

              {/* Timeline */}
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">
                  Timeline
                </h3>
                <Timeline events={app.timeline_events} />
              </div>
            </>
          )}
        </div>

        {/* Footer action */}
        {app && (
          <div className="px-6 py-4 border-t border-slate-700/50">
            <button
              id="update-status-btn"
              onClick={() => setShowUpdateModal(true)}
              className="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white
                         text-sm font-semibold rounded-xl transition-all duration-200
                         shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30"
            >
              Update Status
            </button>
          </div>
        )}
      </aside>

      {/* Slide-in animation */}
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
      `}</style>

      {/* Update status modal */}
      {showUpdateModal && app && (
        <UpdateStatusModal
          app={app}
          onClose={() => setShowUpdateModal(false)}
        />
      )}
    </>
  );
}
