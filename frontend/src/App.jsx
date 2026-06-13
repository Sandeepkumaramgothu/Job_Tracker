// frontend/src/App.jsx

/**
 * Root application component.
 *
 * Layout:
 *   ┌──────────────────────────────────────────────────────┐
 *   │  Sidebar (fixed left, 240px)                         │
 *   │  ┌────────────────────────────────────────────────┐  │
 *   │  │  Main content area (scrollable)               │  │
 *   │  └────────────────────────────────────────────────┘  │
 *   │  DetailPanel (fixed right, slide-in on selection)    │
 *   └──────────────────────────────────────────────────────┘
 *
 * Routing: client-side state (no react-router needed for a single-page
 * tool with only 5 views). This keeps the bundle lean.
 * Trade-off: deep-linking to specific views isn't supported.
 * To add it later, replace `activePage` state with react-router v6 routes.
 *
 * TanStack Query Provider is mounted here so all descendant hooks share
 * the same query cache and deduplication.
 */

import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import Dashboard    from './pages/Dashboard';
import Applications from './pages/Applications';
import FollowUps    from './pages/FollowUps';
import Analytics    from './pages/Analytics';
import Settings     from './pages/Settings';

import DetailPanel         from './components/DetailPanel';
import AddApplicationModal from './components/AddApplicationModal';

// ---------------------------------------------------------------------------
// TanStack Query client — shared across the whole app
// ---------------------------------------------------------------------------
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

// ---------------------------------------------------------------------------
// Nav items
// ---------------------------------------------------------------------------
const NAV_ITEMS = [
  { id: 'dashboard',    label: 'Dashboard',    emoji: '🏠' },
  { id: 'applications', label: 'Applications', emoji: '📋' },
  { id: 'followups',    label: 'Follow-Ups',   emoji: '📧' },
  { id: 'analytics',    label: 'Analytics',    emoji: '📊' },
  { id: 'settings',     label: 'Settings',     emoji: '⚙️'  },
];

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------
function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-60 bg-slate-900/95 border-r
                       border-slate-800 flex flex-col z-20 backdrop-blur-xl">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-violet-600
                          flex items-center justify-center shadow-lg shadow-blue-500/20">
            <span className="text-base">💼</span>
          </div>
          <div>
            <p className="text-sm font-bold text-white leading-tight">Job Tracker</p>
            <p className="text-[10px] text-slate-500 leading-tight">Application Manager</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => {
          const isActive = activePage === item.id;
          return (
            <button
              key={item.id}
              id={`nav-${item.id}`}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm
                          font-medium transition-all duration-150 text-left
                          ${isActive
                            ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="text-base w-5 text-center">{item.emoji}</span>
              {item.label}
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400" />
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-slate-800">
        <p className="text-[10px] text-slate-600 text-center">
          Job Tracker v1.0 · Built with FastAPI + React
        </p>
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Page renderer
// ---------------------------------------------------------------------------
function PageContent({ activePage, onSelectApp, onAddNew }) {
  switch (activePage) {
    case 'dashboard':    return <Dashboard    onSelectApp={onSelectApp} onAddNew={onAddNew} />;
    case 'applications': return <Applications onSelectApp={onSelectApp} onAddNew={onAddNew} />;
    case 'followups':    return <FollowUps    onSelectApp={onSelectApp} />;
    case 'analytics':    return <Analytics />;
    case 'settings':     return <Settings />;
    default:             return <Dashboard    onSelectApp={onSelectApp} onAddNew={onAddNew} />;
  }
}

// ---------------------------------------------------------------------------
// App root
// ---------------------------------------------------------------------------
function AppShell() {
  const [activePage,      setActivePage]      = useState('dashboard');
  const [selectedAppId,   setSelectedAppId]   = useState(null);   // detail panel
  const [showAddModal,    setShowAddModal]     = useState(false);  // add modal

  const handleSelectApp = (id) => setSelectedAppId(id);
  const handleClosePanel = () => setSelectedAppId(null);
  const handleAddNew = () => setShowAddModal(true);
  const handleCreated = (app) => {
    setSelectedAppId(app.id); // auto-open the new application's detail panel
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Sidebar */}
      <Sidebar activePage={activePage} onNavigate={(page) => {
        setActivePage(page);
        setSelectedAppId(null); // close detail when navigating
      }} />

      {/* Main content */}
      <main
        className={`min-h-screen transition-all duration-300 ${
          selectedAppId ? 'mr-[min(512px,100vw)]' : ''
        }`}
        style={{ marginLeft: '240px' }}
      >
        <div className="max-w-4xl mx-auto px-6 py-8">
          <PageContent
            activePage={activePage}
            onSelectApp={handleSelectApp}
            onAddNew={handleAddNew}
          />
        </div>
      </main>

      {/* Detail panel — slide in from right */}
      {selectedAppId && (
        <DetailPanel appId={selectedAppId} onClose={handleClosePanel} />
      )}

      {/* Add application modal */}
      {showAddModal && (
        <AddApplicationModal
          onClose={() => setShowAddModal(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Export with QueryClientProvider
// ---------------------------------------------------------------------------
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell />
    </QueryClientProvider>
  );
}
