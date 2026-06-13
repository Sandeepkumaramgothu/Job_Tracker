// frontend/src/components/Timeline.jsx

/**
 * Vertical timeline of status events for an application.
 * Props: { events } — array of TimelineEventResponse objects, oldest first.
 */

const STATUS_CONFIG = {
  applied:   { label: 'Applied',   dot: 'bg-blue-500',    line: 'bg-blue-500/30'    },
  interview: { label: 'Interview', dot: 'bg-violet-500',  line: 'bg-violet-500/30'  },
  followup:  { label: 'Follow-up', dot: 'bg-amber-500',   line: 'bg-amber-500/30'   },
  offer:     { label: 'Offer',     dot: 'bg-emerald-500', line: 'bg-emerald-500/30' },
  rejected:  { label: 'Rejected',  dot: 'bg-red-500',     line: 'bg-red-500/30'     },
};

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  });
}

export default function Timeline({ events = [] }) {
  if (events.length === 0) {
    return (
      <p className="text-slate-500 text-sm text-center py-6">
        No timeline events yet.
      </p>
    );
  }

  // Sort oldest → newest for display
  const sorted = [...events].sort(
    (a, b) => new Date(a.event_date) - new Date(b.event_date),
  );

  return (
    <ol className="relative space-y-0">
      {sorted.map((event, idx) => {
        const cfg = STATUS_CONFIG[event.status] ?? {
          label: event.status,
          dot: 'bg-slate-500',
          line: 'bg-slate-500/30',
        };
        const isLast = idx === sorted.length - 1;

        return (
          <li key={event.id} className="relative flex gap-4 pb-6">
            {/* Connector line */}
            {!isLast && (
              <div className={`absolute left-[11px] top-6 bottom-0 w-0.5 ${cfg.line}`} />
            )}

            {/* Dot */}
            <div className={`shrink-0 mt-0.5 w-6 h-6 rounded-full ${cfg.dot}
                             ring-4 ring-slate-900 flex items-center justify-center`}>
              <div className="w-2 h-2 rounded-full bg-white/60" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 pt-0.5">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-slate-200">{cfg.label}</span>
                <span className="text-xs text-slate-500">{formatDate(event.event_date)}</span>
              </div>

              {event.note && (
                <p className="text-sm text-slate-400 mb-2">{event.note}</p>
              )}

              {event.interview_date && (
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400
                                bg-violet-500/10 border border-violet-500/20 rounded-lg
                                px-3 py-2 mt-1">
                  <span>
                    <span className="text-slate-500">Interview:</span>{' '}
                    <span className="text-violet-300">{formatDate(event.interview_date)}</span>
                  </span>
                  {event.interview_type && (
                    <span>
                      <span className="text-slate-500">Type:</span>{' '}
                      {event.interview_type}
                    </span>
                  )}
                  {event.interviewer && (
                    <span>
                      <span className="text-slate-500">With:</span>{' '}
                      {event.interviewer}
                    </span>
                  )}
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
