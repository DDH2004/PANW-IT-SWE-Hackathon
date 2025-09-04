import React, { useEffect, useState } from 'react';
import axios from 'axios';

const FLAG_BADGE_COLORS = {
  recurring: 'bg-indigo-100 text-indigo-700',
  trial_converted: 'bg-yellow-100 text-yellow-700',
  small_recurring: 'bg-green-100 text-green-700',
  variable_amount: 'bg-red-100 text-red-700'
};

export default function SubscriptionsPage({ API }) {
  const [subs, setSubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [resolved, setResolved] = useState(()=>{
    try { return JSON.parse(localStorage.getItem('resolved_subscriptions_v1')||'[]'); } catch(_) { return []; }
  });
  const [showResolved, setShowResolved] = useState(false);

  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/subscriptions`)
      .then(r => setSubs(r.data.subscriptions))
      .catch(()=>setError('Failed to load'))
      .finally(()=>setLoading(false));
  }, [API]);

  const toggleResolve = (merchant) => {
    setResolved(prev => {
      if (prev.includes(merchant)) return prev; // already resolved
      const next = [...prev, merchant];
      try { localStorage.setItem('resolved_subscriptions_v1', JSON.stringify(next)); } catch(_){}
      return next;
    });
  };

  const unresolvedSubs = subs.filter(s => !resolved.includes(s.merchant));
  const resolvedSubs = subs.filter(s => resolved.includes(s.merchant));

  if (loading) return <div>Loading...</div>;
  if (error) return <div className="text-red-600 text-sm">{error}</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Recurring & Gray Charges</h2>
      <div className="text-sm text-gray-600 max-w-2xl">Automatically detected recurring merchants, potential free-trial conversions, and small recurring ("gray") charges. Review and cancel unwanted services.</div>
      <div className="flex items-center gap-4 text-xs">
        <span className="font-medium">Unresolved: {unresolvedSubs.length}</span>
        <button onClick={()=>setShowResolved(s=>!s)} className="underline text-indigo-600 disabled:text-gray-400" disabled={resolvedSubs.length===0}>
          {showResolved? 'Hide Resolved':'Show Resolved'} ({resolvedSubs.length})
        </button>
        {resolvedSubs.length>0 && <button onClick={()=>{ setResolved([]); try{localStorage.removeItem('resolved_subscriptions_v1');}catch(_){}; }} className="text-red-500 underline">Reset Resolved</button>}
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        {unresolvedSubs.map(s => <SubscriptionCard key={s.merchant} sub={s} onResolve={toggleResolve} resolved={false} />)}
        {unresolvedSubs.length === 0 && subs.length>0 && <div className="text-sm text-gray-500">All subscriptions resolved.</div>}
        {subs.length === 0 && <div className="text-sm text-gray-500">No recurring patterns detected yet.</div>}
      </div>
      {showResolved && resolvedSubs.length>0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-600 mt-4">Resolved</h3>
          <div className="grid md:grid-cols-2 gap-4 opacity-70">
            {resolvedSubs.map(s => <SubscriptionCard key={s.merchant} sub={s} onResolve={toggleResolve} resolved />)}
          </div>
        </div>
      )}
    </div>
  );
}

function SubscriptionCard({ sub, onResolve, resolved }) {
  return (
    <div className={`bg-white rounded shadow p-4 space-y-2 relative ${resolved? 'border border-dashed border-gray-300':''}`}>
      {resolved && <span className="absolute top-2 right-2 text-[10px] bg-gray-200 text-gray-600 px-2 py-0.5 rounded">Resolved</span>}
      <div className="flex justify-between items-start">
        <div>
          <div className="font-semibold">{sub.merchant}</div>
          <div className="text-xs text-gray-500">Occurrences: {sub.occurrences}</div>
        </div>
        <div className="flex flex-wrap gap-1 justify-end">
          {sub.flags.map(f => <FlagBadge key={f} flag={f} />)}
        </div>
      </div>
      <div className="text-sm flex flex-wrap gap-4">
        <Info label="Avg Interval" value={`${sub.avg_interval_days}d (±${sub.interval_jitter_days})`} />
        <Info label="Avg Amount" value={`$${sub.avg_amount}`} />
        <Info label="Range" value={`$${sub.amount_range[0]}-$${sub.amount_range[1]}`} />
      </div>
      {sub.estimated_next_charge && (
        <div className="text-xs text-gray-600">Next est: <span className="font-medium">{sub.estimated_next_charge}</span></div>
      )}
      {sub.flags.includes('trial_converted') && (
        <div className="text-xs text-yellow-700 bg-yellow-50 p-2 rounded">Possible trial converted to paid – first charge was free/low then increased.</div>
      )}
      {sub.flags.includes('small_recurring') && !sub.flags.includes('trial_converted') && (
        <div className="text-xs text-indigo-700 bg-indigo-50 p-2 rounded">Small recurring charge – consider reviewing necessity.</div>
      )}
      {sub.flags.includes('variable_amount') && (
        <div className="text-xs text-red-700 bg-red-50 p-2 rounded">Variable amount – watch for pricing changes or hidden fees.</div>
      )}
      <div className="flex justify-end gap-2">
        {!resolved && (
          <button
            className="text-xs bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded"
            onClick={()=>{
              // Placeholder for real cancellation flow hook
              try { alert('Pretend cancellation portal / link opened. Marking resolved.'); } catch(_){}
              onResolve && onResolve(sub.merchant);
            }}
          >Review / Cancel / Resolve</button>
        )}
        {resolved && (
          <button
            className="text-[10px] px-2 py-1 rounded border text-gray-600 hover:bg-gray-50"
            onClick={()=>{ /* allow unresolve for quick mistake recovery */
              if (onResolve) {
                // Remove from resolved list by rewriting storage (lift state via custom event not needed; handled in parent reset for simplicity)
                try {
                  const existing = JSON.parse(localStorage.getItem('resolved_subscriptions_v1')||'[]');
                  const next = existing.filter(m=>m!==sub.merchant);
                  localStorage.setItem('resolved_subscriptions_v1', JSON.stringify(next));
                  // crude trigger: dispatch storage event for React not listening; fallback reload state by forcing location reload? Better to avoid.
                  // Simpler approach: window.dispatchEvent(new Event('storage')) is ignored in same tab; so we soft prompt user.
                  alert('Reload page to re-activate this subscription (or click Reset Resolved).');
                } catch(_){ }
              }
            }}
          >Undo</button>
        )}
      </div>
    </div>
  );
}

function FlagBadge({ flag }) {
  return <span className={`text-[10px] uppercase tracking-wide font-semibold px-2 py-1 rounded ${FLAG_BADGE_COLORS[flag] || 'bg-gray-100 text-gray-600'}`}>{flag.replace('_',' ')}</span>;
}

function Info({ label, value }) {
  return (
    <div className="space-y-0.5">
      <div className="text-[10px] uppercase tracking-wide text-gray-500">{label}</div>
      <div className="text-sm font-medium">{value}</div>
    </div>
  );
}
