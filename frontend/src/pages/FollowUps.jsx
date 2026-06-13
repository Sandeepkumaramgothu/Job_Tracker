// frontend/src/pages/FollowUps.jsx

/**
 * Follow-ups page — shows applications that need attention:
 *   1. Upcoming interviews (status=interview, interview_date in the future)
 *   2. Follow-up due (status=applied or followup, date_applied is old)
 *   3. Stale applications (status=applied, no recent update implied by old date)
 *
 * All filtering is done client-side from the full application list.
 * No extra API endpoint needed — the backend mirror logic lives in Celery tasks.
 */

import { useApplications } from '../hooks/useApplications';
import JobCardComp from '../components/JobCard';

const TODAY = new Date();
TODAY.setHours(0, 0, 0, 0);

function daysBetween(dateStr1, dateStr2) {
  const d1 = new Date(dateStr1 + 'T00:00:00');
  const d2 = new Date(dateStr2 + 'T00:00:00');
  return Math.round((d2 - d1) / (1000 * 60 * 60 * 24));
}

function todayStr() {
  return TODAY.toISOString().split('T')[0];
}

// ---------------------------------------------------------------------------
// Section wrapper
// ---------------------------------------------------------------------------
function Section({ title, emoji, count, children }) {
  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xl">{emoji}</span>
        <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest">
          {title}
        </h2>
        <span className="ml-auto text-xs font-semibold px-2 py-0.5
                         bg-slate-800 border border-slate-700 rounded-full text-slate-400">
          {count}
        </span>
      </div>
      {children}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------
function EmptySection({ message }) {
  return (
    <div className="py-6 px-4 text-center text-slate-500 text-sm
                    bg-slate-800/40 border border-slate-700/50 rounded-xl">
      {message}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FollowUps page
// ---------------------------------------------------------------------------
export default function FollowUps({ onSelectApp }) {
  const { data: apps, isLoading, error } = useApplications({});

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="animate-pulse bg-slate-800/60 rounded-xl h-20
                                  border border-slate-700/50" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20
                      rounded-xl p-5">
        Failed to load applications. {error.userMessage}
      </div>
    );
  }

  const today = todayStr();

  // 1. Upcoming interviews — status=interview, interview_date >= today
  //    Sourced from the application list (no timeline available in list view —
  //    we surface this from status only; exact interview_date is in the detail)
  const upcomingInterviews = (apps || []).filter(
    (a) => a.status === 'interview',
  );

  // 2. Follow-up due — status=applied or followup, applied 7+ days ago
  const FOLLOWUP_DAYS = 7;
  const followupDue = (apps || []).filter((a) => {
    if (!['applied', 'followup'].includes(a.status)) return false;
    return daysBetween(a.date_applied, today) >= FOLLOWUP_DAYS;
  });

  // 3. Stale — status=applied, applied 14+ days ago (conservative threshold for UI)
  const STALE_DAYS = 14;
  const stale = (apps || []).filter((a) => {
    if (a.status !== 'applied') return false;
    return daysBetween(a.date_applied, today) >= STALE_DAYS;
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Follow-Ups</h1>
        <p className="text-slate-400 text-sm mt-1">
          Applications that need your attention
        </p>
      </div>

      {/* Upcoming interviews */}
      <Section title="Upcoming Interviews" emoji="🎙️" count={upcomingInterviews.length}>
        {upcomingInterviews.length === 0 ? (
          <EmptySection message="No interviews scheduled. Good luck out there! 🤞" />
        ) : (
          <div className="space-y-3">
            {upcomingInterviews.map((app) => (
              <div key={app.id} className="relative">
                <JobCardComp app={app} onClick={() => onSelectApp(app.id)} />
                <span className="absolute top-3 right-14 text-[10px] font-bold
                                 text-violet-300 bg-violet-500/20 border border-violet-500/30
                                 px-2 py-0.5 rounded-full">
                  Interview
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Follow-up due */}
      <Section title={`Follow-up Due (${FOLLOWUP_DAYS}+ days)`} emoji="📧" count={followupDue.length}>
        {followupDue.length === 0 ? (
          <EmptySection message="No follow-ups due. You're on top of it! ✅" />
        ) : (
          <div className="space-y-3">
            {followupDue.map((app) => {
              const days = daysBetween(app.date_applied, today);
              return (
                <div key={app.id} className="relative">
                  <JobCardComp app={app} onClick={() => onSelectApp(app.id)} />
                  <span className="absolute top-3 right-14 text-[10px] font-bold
                                   text-amber-300 bg-amber-500/20 border border-amber-500/30
                                   px-2 py-0.5 rounded-full">
                    {days}d ago
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Section>

      {/* Stale */}
      <Section title={`Stale (${STALE_DAYS}+ days, no update)`} emoji="⚠️" count={stale.length}>
        {stale.length === 0 ? (
          <EmptySection message="No stale applications. Keep the momentum going!" />
        ) : (
          <div className="space-y-3">
            {stale.map((app) => {
              const days = daysBetween(app.date_applied, today);
              return (
                <div key={app.id} className="relative">
                  <JobCardComp app={app} onClick={() => onSelectApp(app.id)} />
                  <span className="absolute top-3 right-14 text-[10px] font-bold
                                   text-red-400 bg-red-500/20 border border-red-500/30
                                   px-2 py-0.5 rounded-full">
                    {days}d stale
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Section>
    </div>
  );
}
