// frontend/src/pages/Applications.jsx

import { useState } from 'react';
import { useApplications, useDeleteApplication } from '../hooks/useApplications';
import JobCard from '../components/JobCard';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'applied',   label: 'Applied' },
  { value: 'interview', label: 'Interview' },
  { value: 'followup',  label: 'Follow-up' },
  { value: 'offer',     label: 'Offer' },
  { value: 'rejected',  label: 'Rejected' },
];

// ---------------------------------------------------------------------------
// Skeleton row
// ---------------------------------------------------------------------------
function SkeletonRow() {
  return (
    <div className="animate-pulse bg-slate-800/60 rounded-xl h-24
                    border border-slate-700/50" />
  );
}

// ---------------------------------------------------------------------------
// Applications page
// ---------------------------------------------------------------------------
export default function Applications({ onSelectApp, onAddNew }) {
  const [statusFilter, setStatusFilter] = useState('');
  const [searchValue, setSearchValue]   = useState('');
  const [searchQuery, setSearchQuery]   = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null); // id to delete

  const filters = {
    ...(statusFilter && { status: statusFilter }),
    ...(searchQuery  && { search: searchQuery }),
  };

  const { data: apps, isLoading, error } = useApplications(filters);
  const deleteMutation = useDeleteApplication();

  // Debounce search — only fire the query when user stops typing
  const handleSearchChange = (e) => {
    setSearchValue(e.target.value);
  };
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setSearchQuery(searchValue);
  };

  const handleDelete = async (id) => {
    await deleteMutation.mutateAsync(id);
    setConfirmDelete(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Applications</h1>
          <p className="text-slate-400 text-sm mt-1">
            {apps ? `${apps.length} application${apps.length !== 1 ? 's' : ''}` : 'Loading…'}
            {statusFilter && ` · filtered by ${statusFilter}`}
            {searchQuery  && ` · searching "${searchQuery}"`}
          </p>
        </div>
        <button
          id="applications-add-btn"
          onClick={onAddNew}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500
                     text-white text-sm font-semibold rounded-xl
                     transition-all duration-200 shadow-lg shadow-blue-600/20
                     hover:shadow-blue-500/30 hover:-translate-y-0.5"
        >
          <span className="text-base">+</span> Add Application
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex-1 flex gap-2">
          <input
            id="search-input"
            type="text"
            value={searchValue}
            onChange={handleSearchChange}
            placeholder="Search job title or company…"
            className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5
                       text-sm text-slate-100 placeholder-slate-500
                       focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                       transition-colors"
          />
          <button
            type="submit"
            className="px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-200
                       text-sm rounded-xl transition-colors border border-slate-600"
          >
            Search
          </button>
          {searchQuery && (
            <button
              type="button"
              onClick={() => { setSearchValue(''); setSearchQuery(''); }}
              className="px-3 py-2.5 text-slate-400 hover:text-slate-200 text-sm
                         transition-colors"
            >
              ✕
            </button>
          )}
        </form>

        {/* Status filter */}
        <select
          id="status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5
                     text-sm text-slate-100 focus:outline-none focus:border-blue-500
                     focus:ring-1 focus:ring-blue-500 transition-colors cursor-pointer"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3">
          {[0, 1, 2, 3].map((i) => <SkeletonRow key={i} />)}
        </div>
      ) : error ? (
        <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl p-5">
          <p className="font-semibold">Failed to load applications</p>
          <p className="mt-1 opacity-75">{error.userMessage}</p>
        </div>
      ) : apps.length === 0 ? (
        <div className="text-center py-20 text-slate-500">
          <div className="text-5xl mb-4">🔍</div>
          <p className="font-medium text-slate-400 text-lg">
            {searchQuery || statusFilter ? 'No matching applications' : 'No applications yet'}
          </p>
          <p className="text-sm mt-2">
            {searchQuery || statusFilter
              ? 'Try adjusting your search or filter.'
              : 'Add your first application to get started.'}
          </p>
          {!searchQuery && !statusFilter && (
            <button
              onClick={onAddNew}
              className="mt-6 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white
                         text-sm font-semibold rounded-xl transition-all duration-200"
            >
              + Add Application
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {apps.map((app) => (
            <JobCard
              key={app.id}
              app={app}
              onClick={() => onSelectApp(app.id)}
              onDelete={() => setConfirmDelete(app.id)}
            />
          ))}
        </div>
      )}

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4
                        bg-black/60 backdrop-blur-sm"
          onClick={() => setConfirmDelete(null)}
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-sm
                       shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-white mb-2">Delete Application?</h3>
            <p className="text-slate-400 text-sm mb-6">
              This will permanently delete the application and all its timeline events.
              This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDelete(null)}
                className="flex-1 px-4 py-2.5 bg-slate-800 hover:bg-slate-700
                           text-slate-300 text-sm font-semibold rounded-xl
                           border border-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                id="confirm-delete-btn"
                onClick={() => handleDelete(confirmDelete)}
                disabled={deleteMutation.isPending}
                className="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-500
                           text-white text-sm font-semibold rounded-xl transition-colors
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
