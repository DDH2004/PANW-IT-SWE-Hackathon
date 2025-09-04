import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function SettingsPage({ API }) {
  const [budget, setBudget] = useState('');
  const [status, setStatus] = useState('');
  const [wipeStatus, setWipeStatus] = useState('');
  const [confirming, setConfirming] = useState(false);

  const load = async () => {
    try {
      const r = await axios.get(`${API}/settings/MONTHLY_BUDGET`);
      setBudget(r.data.value);
    } catch {
      // not set
    }
  };
  useEffect(()=>{ load(); }, [API]);

  const save = async () => {
    await axios.put(`${API}/settings/MONTHLY_BUDGET`, { value: budget });
    setStatus('Saved');
    setTimeout(()=>setStatus(''), 1500);
  };

  const wipeAll = async () => {
    if(!confirming) {
      setConfirming(true);
      setTimeout(()=>setConfirming(false), 8000); // auto-cancel
      return;
    }
    try {
      const r = await axios.post(`${API}/admin/wipe`);
      setWipeStatus(`Data wiped (transactions:${r.data.deleted.transactions}, categories:${r.data.deleted.transaction_categories})`);
      setConfirming(false);
      setTimeout(()=>setWipeStatus(''), 6000);
    } catch (e) {
      setWipeStatus('Wipe failed');
      setTimeout(()=>setWipeStatus(''), 4000);
    }
  };

  return (
    <div className="space-y-6 max-w-md bg-white p-4 rounded shadow">
      <h2 className="font-semibold">Settings</h2>
      <label className="block text-sm text-gray-600 mb-1">Monthly Budget</label>
      <input className="border p-2 w-full" type="number" value={budget} onChange={e=>setBudget(e.target.value)} placeholder="e.g. 2000" />
      <button className="bg-indigo-600 text-white px-4 py-2 rounded" onClick={save}>Save</button>
      {status && <div className="text-green-600 text-sm">{status}</div>}
      <div className="pt-4 border-t space-y-3">
        <div className="text-sm font-semibold text-red-600 flex items-center gap-2">Danger Zone</div>
        <p className="text-xs text-gray-600">This will permanently delete ALL transactions, categories, goals, and settings. This action cannot be undone.</p>
        <button onClick={wipeAll} className={`px-4 py-2 rounded text-sm font-medium border ${confirming? 'bg-red-600 text-white border-red-600':'bg-white text-red-600 border-red-300 hover:bg-red-50'}`}>
          {confirming? 'Click again to confirm wipe' : 'Wipe All Data'}
        </button>
        {wipeStatus && <div className="text-xs text-red-600">{wipeStatus}</div>}
      </div>
    </div>
  );
}
