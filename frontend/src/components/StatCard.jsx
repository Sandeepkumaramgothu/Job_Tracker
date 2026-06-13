// frontend/src/components/StatCard.jsx

/**
 * A single KPI tile used on the Dashboard.
 * Props: { label, value, icon, color }
 */
export default function StatCard({ label, value, icon, color }) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl p-5 border border-slate-700/50
                  bg-gradient-to-br ${color} backdrop-blur-sm
                  transition-transform duration-200 hover:-translate-y-0.5`}
    >
      {/* Background glow */}
      <div className="absolute -top-4 -right-4 text-6xl opacity-10 select-none">
        {icon}
      </div>

      <div className="relative">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">
          {label}
        </p>
        <p className="text-3xl font-bold text-white tabular-nums">{value}</p>
      </div>
    </div>
  );
}
