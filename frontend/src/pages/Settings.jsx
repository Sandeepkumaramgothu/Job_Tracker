// frontend/src/pages/Settings.jsx

/**
 * Settings page — notification preferences.
 * Loads current settings via useNotificationSettings().
 * Saves via useSaveNotificationSettings().
 * Sends a test email via useSendTestEmail().
 * All inputs are controlled with useState.
 */

import { useEffect, useState } from 'react';
import {
  useNotificationSettings,
  useSaveNotificationSettings,
  useSendTestEmail,
} from '../hooks/useNotifications';

const DEFAULTS = {
  email: '',
  notify_interview: true,
  notify_followup:  true,
  notify_stale:     true,
  weekly_summary:   false,
  followup_freq_days: 7,
};

// ---------------------------------------------------------------------------
// Toggle switch
// ---------------------------------------------------------------------------
function Toggle({ id, checked, onChange, label, description }) {
  return (
    <label
      htmlFor={id}
      className="flex items-center justify-between gap-4 py-4
                 border-b border-slate-800 cursor-pointer group"
    >
      <div>
        <p className="text-sm font-medium text-slate-200 group-hover:text-white
                      transition-colors">
          {label}
        </p>
        {description && (
          <p className="text-xs text-slate-500 mt-0.5">{description}</p>
        )}
      </div>
      <div className="relative shrink-0">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only"
        />
        <div className={`w-10 h-6 rounded-full transition-colors duration-200
                         ${checked ? 'bg-blue-600' : 'bg-slate-700'}`}>
          <div className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full
                           shadow-sm transition-transform duration-200
                           ${checked ? 'translate-x-4' : 'translate-x-0'}`} />
        </div>
      </div>
    </label>
  );
}

// ---------------------------------------------------------------------------
// Settings page
// ---------------------------------------------------------------------------
export default function Settings() {
  const [form, setForm] = useState(DEFAULTS);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [testSuccess, setTestSuccess] = useState(false);
  const [testError,   setTestError]   = useState(null);

  const { data: settings, isLoading } = useNotificationSettings();
  const saveMutation = useSaveNotificationSettings();
  const testMutation = useSendTestEmail();

  // Populate form when settings load
  useEffect(() => {
    if (settings) {
      setForm({
        email:              settings.email,
        notify_interview:   settings.notify_interview,
        notify_followup:    settings.notify_followup,
        notify_stale:       settings.notify_stale,
        weekly_summary:     settings.weekly_summary,
        followup_freq_days: settings.followup_freq_days,
      });
    }
  }, [settings]);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setSaveSuccess(false);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaveSuccess(false);
    try {
      await saveMutation.mutateAsync(form);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      // error surfaced via saveMutation.error
    }
  };

  const handleTestEmail = async () => {
    setTestSuccess(false);
    setTestError(null);
    try {
      await testMutation.mutateAsync();
      setTestSuccess(true);
      setTimeout(() => setTestSuccess(false), 4000);
    } catch (err) {
      setTestError(err.userMessage || 'Failed to send test email.');
    }
  };

  return (
    <div className="space-y-8 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-slate-400 text-sm mt-1">
          Configure email reminders and notification preferences
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">

        {/* Email address */}
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
          <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-4">
            Notification Email
          </h2>
          {isLoading ? (
            <div className="animate-pulse h-10 bg-slate-700 rounded-xl" />
          ) : (
            <input
              id="settings-email"
              type="email"
              value={form.email}
              onChange={(e) => handleChange('email', e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5
                         text-sm text-slate-100 placeholder-slate-500
                         focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                         transition-colors"
            />
          )}
        </div>

        {/* Notification toggles */}
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
          <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-2">
            Reminders
          </h2>

          <Toggle
            id="toggle-interview"
            checked={form.notify_interview}
            onChange={(v) => handleChange('notify_interview', v)}
            label="Interview reminders"
            description="Send an email 24 hours before a scheduled interview"
          />
          <Toggle
            id="toggle-followup"
            checked={form.notify_followup}
            onChange={(v) => handleChange('notify_followup', v)}
            label="Follow-up reminders"
            description="Alert when a follow-up email is due"
          />
          <Toggle
            id="toggle-stale"
            checked={form.notify_stale}
            onChange={(v) => handleChange('notify_stale', v)}
            label="Stale application alerts"
            description="Notify when an application has had no update in 7+ days"
          />
          <Toggle
            id="toggle-weekly"
            checked={form.weekly_summary}
            onChange={(v) => handleChange('weekly_summary', v)}
            label="Weekly summary"
            description="Monday morning digest of your job search progress"
          />

          {/* Follow-up frequency */}
          <div className="pt-4">
            <label htmlFor="settings-freq" className="block text-sm font-medium
                                                       text-slate-200 mb-1">
              Follow-up frequency
            </label>
            <p className="text-xs text-slate-500 mb-2">
              How many days between follow-up reminders
            </p>
            <div className="flex items-center gap-3">
              <input
                id="settings-freq"
                type="number"
                min="1"
                max="365"
                value={form.followup_freq_days}
                onChange={(e) => handleChange('followup_freq_days', Number(e.target.value))}
                className="w-24 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2
                           text-sm text-slate-100 text-center
                           focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                           transition-colors"
              />
              <span className="text-sm text-slate-400">days</span>
            </div>
          </div>
        </div>

        {/* Save error */}
        {saveMutation.error && (
          <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20
                          rounded-xl p-4">
            {saveMutation.error.userMessage}
          </div>
        )}

        {/* Save button */}
        <div className="flex items-center gap-4">
          <button
            id="settings-save-btn"
            type="submit"
            disabled={saveMutation.isPending}
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm
                       font-semibold rounded-xl transition-all duration-200
                       shadow-lg shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saveMutation.isPending ? 'Saving…' : 'Save Settings'}
          </button>
          {saveSuccess && (
            <span className="text-sm text-emerald-400 flex items-center gap-1.5">
              <span>✓</span> Settings saved!
            </span>
          )}
        </div>
      </form>

      {/* Test email */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
        <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-2">
          Test Notifications
        </h2>
        <p className="text-sm text-slate-400 mb-4">
          Send a test email to verify your notification configuration is working.
        </p>
        <div className="flex items-center gap-4 flex-wrap">
          <button
            id="send-test-email-btn"
            type="button"
            onClick={handleTestEmail}
            disabled={testMutation.isPending || !form.email || !settings}
            className="px-5 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm
                       font-semibold rounded-xl border border-slate-600
                       transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {testMutation.isPending ? 'Sending…' : 'Send Test Email'}
          </button>
          {testSuccess && (
            <span className="text-sm text-emerald-400">✓ Test email sent!</span>
          )}
          {testError && (
            <span className="text-sm text-red-400">{testError}</span>
          )}
        </div>
        {!settings && !isLoading && (
          <p className="text-xs text-amber-400 mt-3">
            Save your settings first before sending a test email.
          </p>
        )}
      </div>
    </div>
  );
}
