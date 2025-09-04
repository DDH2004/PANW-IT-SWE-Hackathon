import React from 'react';

/**
 * OnboardingOverlay
 * Lightweight first-visit overlay to orient the user.
 * Props:
 *  - onDismiss(): mark onboarding as seen
 *  - onAction(viewKey: string): switch main view (also dismiss)
 */
export default function OnboardingOverlay({ onDismiss, onAction }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-indigo-950/70 backdrop-blur-sm">
      <div className="w-full max-w-3xl mx-auto bg-white rounded-lg shadow-2xl p-8 relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-72 h-72 bg-indigo-100 rounded-full blur-3xl opacity-60 pointer-events-none" />
        <div className="absolute -bottom-16 -left-10 w-60 h-60 bg-violet-100 rounded-full blur-2xl opacity-70 pointer-events-none" />
        <div className="relative space-y-6">
          <header className="space-y-2">
            <h1 className="text-2xl font-bold text-indigo-700">Welcome to Your Financial Coach</h1>
            <p className="text-sm text-gray-600 leading-relaxed">
              A quick start: upload your transactions, explore insights, chat with the coach, and set goals to personalize guidance.
            </p>
          </header>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card
              title="1. Upload"
              body="Import a CSV of transactions so dashboards & coaching have context."
              actionLabel="Upload CSV"
              onClick={() => onAction('upload')}
              accent="indigo"
            />
            <Card
              title="2. Dashboard"
              body="View spending trends & filter by timeframe (1M / 1Y / All)."
              actionLabel="Open"
              onClick={() => onAction('dashboard')}
              accent="violet"
            />
            <Card
              title="3. Coach"
              body="Ask for savings ideas or clarify unusual spending."
              actionLabel="Chat"
              onClick={() => onAction('coach')}
              accent="sky"
            />
            <Card
              title="4. Goals"
              body="Define savings or payoff targets to shape advice."
              actionLabel="Set Goal"
              onClick={() => onAction('goals')}
              accent="emerald"
            />
          </div>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={() => onAction('upload')}
                className="px-5 py-2.5 rounded bg-indigo-600 text-white text-sm font-medium shadow hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >Get Started</button>
              <button
                onClick={onDismiss}
                className="px-4 py-2 rounded border border-gray-300 text-gray-700 text-sm hover:bg-gray-50"
              >Maybe Later</button>
              <label className="ml-auto flex items-center gap-2 text-[11px] text-gray-500">
                <input type="checkbox" defaultChecked readOnly /> Don't show again
              </label>
            </div>

          <p className="text-[11px] text-gray-400 pt-2 border-t">
            We store only what's needed for personalization. You can clear history anytime in Settings.
          </p>
        </div>
      </div>
    </div>
  );
}

function Card({ title, body, actionLabel, onClick, accent }) {
  const accentMap = {
    indigo: 'from-indigo-50 to-indigo-100 hover:shadow-indigo-200',
    violet: 'from-violet-50 to-violet-100 hover:shadow-violet-200',
    sky: 'from-sky-50 to-sky-100 hover:shadow-sky-200',
    emerald: 'from-emerald-50 to-emerald-100 hover:shadow-emerald-200',
  };
  return (
    <div className={`group relative rounded-md border bg-gradient-to-br ${accentMap[accent] || 'from-gray-50 to-white'} p-4 flex flex-col shadow-sm transition-shadow`}> 
      <h3 className="font-medium text-sm text-gray-800 mb-1">{title}</h3>
      <p className="text-[11px] text-gray-600 flex-1 leading-relaxed">{body}</p>
      <button
        onClick={onClick}
        className="mt-3 self-start text-[11px] font-medium px-2 py-1 rounded bg-white border border-gray-200 shadow-sm hover:bg-gray-50 active:scale-[.97]"
      >{actionLabel}</button>
      <div className="absolute inset-0 rounded-md ring-1 ring-transparent group-hover:ring-indigo-200 pointer-events-none" />
    </div>
  );
}
