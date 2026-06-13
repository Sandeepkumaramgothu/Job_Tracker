// frontend/src/components/JobCard.jsx

/**
 * A single application row used in the Dashboard and Applications list.
 * Props:
 *   app      — ApplicationResponse object
 *   onClick  — fired when the card body is clicked (open detail panel)
 *   onDelete — fired when the delete button is clicked (optional)
 */

const STATUS_CONFIG = {
  applied:   { label: 'Applied',    classes: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
  interview: { label: 'Interview',  classes: 'bg-violet-500/20 text-violet-300 border-violet-500/30' },
  followup:  { label: 'Follow-up',  classes: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
  offer:     { label: 'Offer',      classes: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
  rejected:  { label: 'Rejected',   classes: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

export default function JobCard({ app, onClick, onDelete }) {
  const status = STATUS_CONFIG[app.status] ?? { label: app.status, classes: 'bg-slate-700 text-slate-300 border-slate-600' };

  return (
    <div
      className="group relative flex items-center gap-4 p-4 rounded-xl
                 bg-slate-800/60 border border-slate-700/50 cursor-pointer
                 hover:bg-slate-800 hover:border-slate-600
                 transition-all duration-200 hover:-translate-y-0.5
                 hover:shadow-lg hover:shadow-black/20"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      aria-label={`Open ${app.job_title} at ${app.company}`}
    >
      {/* Company initial avatar */}
      <div className="shrink-0 w-11 h-11 rounded-xl bg-gradient-to-br from-slate-700 to-slate-600
                      flex items-center justify-center text-lg font-bold text-slate-300
                      border border-slate-600/50">
        {app.company.charAt(0).toUpperCase()}
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <p className="font-semibold text-white text-sm truncate">{app.job_title}</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="font-medium text-slate-300">{app.company}</span>
          {app.location && (
            <>
              <span className="text-slate-600">·</span>
              <span>{app.location}</span>
            </>
          )}
          {app.salary_range && (
            <>
              <span className="text-slate-600">·</span>
              <span className="text-emerald-400">{app.salary_range}</span>
            </>
          )}
        </div>
      </div>

      {/* Right side */}
      <div className="shrink-0 flex flex-col items-end gap-2">
        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${status.classes}`}>
          {status.label}
        </span>
        <span className="text-xs text-slate-500">{formatDate(app.date_applied)}</span>
      </div>

      {/* Delete button — only visible on hover when onDelete is provided */}
      {onDelete && (
        <button
          id={`delete-app-${app.id}`}
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="shrink-0 ml-1 p-2 rounded-lg text-slate-600 hover:text-red-400
                     hover:bg-red-500/10 opacity-0 group-hover:opacity-100
                     transition-all duration-150"
          aria-label={`Delete ${app.job_title} at ${app.company}`}
          title="Delete application"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd"
              d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
              clipRule="evenodd" />
          </svg>
        </button>
      )}
    </div>
  );
}
