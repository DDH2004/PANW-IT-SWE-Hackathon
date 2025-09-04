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

  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/subscriptions`)
      .then(r => setSubs(r.data.subscriptions))
      .catch(()=>setError('Failed to load'))
      .finally(()=>setLoading(false));
  }, [API]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div className="text-red-600 text-sm">{error}</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Recurring & Gray Charges</h2>
      <div className="text-sm text-gray-600 max-w-2xl">Automatically detected recurring merchants, potential free-trial conversions, and small recurring ("gray") charges. Review and cancel unwanted services.</div>
      <div className="grid md:grid-cols-2 gap-4">
        {subs.map(s => <SubscriptionCard key={s.merchant} sub={s} />)}
        {subs.length === 0 && <div className="text-sm text-gray-500">No recurring patterns detected yet.</div>}
      </div>
    </div>
  );
}

function SubscriptionCard({ sub }) {
  return (
    <div className="bg-white rounded shadow p-4 space-y-2">
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
      <div className="flex justify-end">
        <button className="text-xs bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded" onClick={()=>alert('Implement cancellation flow / provider link')}>Review / Cancel</button>
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
