// frontend/src/pages/Dashboard.jsx

import { useAnalytics } from '../hooks/useAnalytics';
import { useApplications } from '../hooks/useApplications';
import StatCard from '../components/StatCard';
import JobCard from '../components/JobCard';

const STATUS_COLORS = {
  applied:   'bg-blue-500/20 text-blue-300 border border-blue-500/30',
  interview: 'bg-violet-500/20 text-violet-300 border border-violet-500/30',
  followup:  'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  offer:     'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
  rejected:  'bg-red-500/20 text-red-400 border border-red-500/30',
};

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------
function SkeletonCard() {
  return (
    <div className="animate-pulse bg-slate-800/60 rounded-2xl p-5 border border-slate-700/50">
      <div className="h-3 bg-slate-700 rounded w-1/3 mb-3" />
      <div className="h-7 bg-slate-700 rounded w-1/2 mb-1" />
      <div className="h-3 bg-slate-700 rounded w-2/3" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export default function Dashboard({ onSelectApp, onAddNew }) {
  const { data: analytics, isLoading: analyticsLoading, error: analyticsError } = useAnalytics();
  const { data: apps, isLoading: appsLoading, error: appsError } = useApplications({});

  const statCards = analytics
    ? [
        {
          label: 'Total Applications',
          value: Object.values(analytics.count_by_status).reduce((a, b) => a + b, 0),
          icon: '📋',
          color: 'from-blue-600/30 to-blue-800/10',
        },
        {
          label: 'This Month',
          value: analytics.applications_this_month,
          icon: '📅',
          color: 'from-violet-600/30 to-violet-800/10',
        },
        {
          label: 'Interview Rate',
          value: `${analytics.interview_conversion_rate}%`,
          icon: '🎯',
          color: 'from-emerald-600/30 to-emerald-800/10',
        },
        {
          label: 'Avg. Days to Response',
          value: analytics.avg_days_to_first_response !== null
            ? `${analytics.avg_days_to_first_response}d`
            : '—',
          icon: '⚡',
          color: 'from-amber-600/30 to-amber-800/10',
        },
      ]
    : [];

  // Recent = last 5 apps sorted by date_applied desc
  const recentApps = apps
    ? [...apps]
        .sort((a, b) => new Date(b.date_applied) - new Date(a.date_applied))
        .slice(0, 5)
    : [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">Your job search at a glance</p>
        </div>
        <button
          id="dashboard-add-btn"
          onClick={onAddNew}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500
                     text-white text-sm font-semibold rounded-xl
                     transition-all duration-200 shadow-lg shadow-blue-600/20
                     hover:shadow-blue-500/30 hover:-translate-y-0.5"
        >
          <span className="text-base">+</span> Add Application
        </button>
      </div>

      {/* Stat cards */}
      <section aria-label="Statistics">
        {analyticsLoading ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)}
          </div>
        ) : analyticsError ? (
          <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl p-4">
            Failed to load analytics. Check that the backend is running.
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {statCards.map((card) => (
              <StatCard key={card.label} {...card} />
            ))}
          </div>
        )}
      </section>

      {/* Status breakdown */}
      {analytics && (
        <section aria-label="Status breakdown">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-3">
            Pipeline
          </h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(analytics.count_by_status).map(([status, count]) => (
              <span
                key={status}
                className={`px-3 py-1 rounded-full text-xs font-semibold ${STATUS_COLORS[status] || 'bg-slate-700 text-slate-300'}`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}: {count}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Top companies */}
      {analytics?.top_companies?.length > 0 && (
        <section aria-label="Top companies">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-3">
            Most Applied To
          </h2>
          <div className="flex flex-wrap gap-2">
            {analytics.top_companies.map((company, i) => (
              <span
                key={company}
                className="flex items-center gap-1.5 px-3 py-1 bg-slate-800
                           border border-slate-700 rounded-full text-xs text-slate-300"
              >
                <span className="text-slate-500 font-mono">#{i + 1}</span>
                {company}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Recent applications */}
      <section aria-label="Recent applications">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-widest">
            Recent Applications
          </h2>
        </div>

        {appsLoading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="animate-pulse bg-slate-800/60 rounded-xl h-20
                                      border border-slate-700/50" />
            ))}
          </div>
        ) : appsError ? (
          <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl p-4">
            Failed to load applications.
          </div>
        ) : recentApps.length === 0 ? (
          <div className="text-center py-16 text-slate-500">
            <div className="text-4xl mb-3">📭</div>
            <p className="font-medium text-slate-400">No applications yet</p>
            <p className="text-sm mt-1">Click "Add Application" to get started.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recentApps.map((app) => (
              <JobCard key={app.id} app={app} onClick={() => onSelectApp(app.id)} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
