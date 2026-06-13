// frontend/src/pages/Analytics.jsx

/**
 * Analytics page — visual summary of the job search.
 * Displays all metrics from GET /api/analytics/summary.
 * Uses pure CSS/Tailwind bar charts — no extra chart library needed.
 */

import { useAnalytics } from '../hooks/useAnalytics';
import StatCard from '../components/StatCard';

const STATUS_CONFIG = {
  applied:   { label: 'Applied',   color: 'bg-blue-500' },
  interview: { label: 'Interview', color: 'bg-violet-500' },
  followup:  { label: 'Follow-up', color: 'bg-amber-500' },
  offer:     { label: 'Offer',     color: 'bg-emerald-500' },
  rejected:  { label: 'Rejected',  color: 'bg-red-500' },
};

// ---------------------------------------------------------------------------
// Horizontal bar chart row
// ---------------------------------------------------------------------------
function BarRow({ label, count, total, color }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 text-xs text-slate-400 text-right shrink-0">{label}</span>
      <div className="flex-1 bg-slate-800 rounded-full h-2.5 overflow-hidden">
        <div
          className={`${color} h-full rounded-full transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-xs text-slate-400 tabular-nums">{count}</span>
      <span className="w-8 text-xs text-slate-500 tabular-nums">{pct}%</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------
function Skeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[0,1,2,3].map((i) => (
          <div key={i} className="h-28 bg-slate-800/60 rounded-2xl border border-slate-700/50" />
        ))}
      </div>
      <div className="h-64 bg-slate-800/60 rounded-2xl border border-slate-700/50" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Analytics page
// ---------------------------------------------------------------------------
export default function Analytics() {
  const { data, isLoading, error } = useAnalytics();

  if (isLoading) return <Skeleton />;

  if (error) {
    return (
      <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl p-5">
        <p className="font-semibold">Failed to load analytics</p>
        <p className="mt-1 opacity-75">{error.userMessage}</p>
      </div>
    );
  }

  const total = Object.values(data.count_by_status).reduce((a, b) => a + b, 0);

  const statCards = [
    {
      label: 'Total Applications',
      value: total,
      icon: '📋',
      color: 'from-blue-600/30 to-blue-800/10',
    },
    {
      label: 'This Month',
      value: data.applications_this_month,
      icon: '📅',
      color: 'from-violet-600/30 to-violet-800/10',
    },
    {
      label: 'Interview Rate',
      value: `${data.interview_conversion_rate}%`,
      icon: '🎯',
      color: 'from-emerald-600/30 to-emerald-800/10',
    },
    {
      label: 'Avg. Days to Response',
      value: data.avg_days_to_first_response !== null
        ? `${data.avg_days_to_first_response}d`
        : '—',
      icon: '⚡',
      color: 'from-amber-600/30 to-amber-800/10',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Analytics</h1>
        <p className="text-slate-400 text-sm mt-1">Your job search performance at a glance</p>
      </div>

      {/* KPI stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </div>

      {/* Status breakdown bar chart */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
        <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-6">
          Pipeline Breakdown
        </h2>
        {total === 0 ? (
          <p className="text-center text-slate-500 text-sm py-8">
            No applications yet. Start applying!
          </p>
        ) : (
          <div className="space-y-4">
            {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
              <BarRow
                key={key}
                label={cfg.label}
                count={data.count_by_status[key] ?? 0}
                total={total}
                color={cfg.color}
              />
            ))}
          </div>
        )}
      </div>

      {/* Top companies */}
      {data.top_companies.length > 0 && (
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
          <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-4">
            Most Applied To
          </h2>
          <ol className="space-y-3">
            {data.top_companies.map((company, i) => (
              <li key={company} className="flex items-center gap-3">
                <span className="w-6 h-6 flex items-center justify-center rounded-full
                                 bg-slate-700 text-xs font-bold text-slate-400">
                  {i + 1}
                </span>
                <span className="text-sm font-medium text-slate-200">{company}</span>
                {i === 0 && (
                  <span className="text-xs text-amber-400 ml-auto">🏆 Top</span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Insight callout */}
      {total > 0 && (
        <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/20
                        rounded-xl text-sm text-blue-200">
          <span className="text-lg shrink-0">💡</span>
          <p>
            {data.interview_conversion_rate > 20
              ? `Strong interview rate of ${data.interview_conversion_rate}%! Your applications are resonating well.`
              : data.interview_conversion_rate > 0
              ? `Interview rate is ${data.interview_conversion_rate}%. Consider tailoring your resume more closely to each job description.`
              : 'No interviews yet — keep applying and refining your applications.'}
          </p>
        </div>
      )}
    </div>
  );
}
