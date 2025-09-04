import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function GoalsPage({ API }) {
  const [goals, setGoals] = useState([]);
  const [form, setForm] = useState({ name: '', target_amount: '', target_date: '' });
  const [forecasts, setForecasts] = useState({}); // goalId -> { data, loading, error, open }

  const load = () => axios.get(`${API}/goals/`).then(r => setGoals(r.data));
  useEffect(() => { load(); }, [API]);

  const create = async () => {
    if(!form.name || !form.target_amount) return;
    const payload = { name: form.name, target_amount: parseFloat(form.target_amount) };
    if (form.target_date) payload.target_date = form.target_date; // ISO date
    await axios.post(`${API}/goals/`, payload);
    setForm({ name: '', target_amount: '', target_date: '' });
    load();
  };

  const update = async (id, patch) => {
    await axios.patch(`${API}/goals/${id}`, patch);
    load();
  };

  const remove = async (id) => {
    await axios.delete(`${API}/goals/${id}`);
    load();
  };

  const toggleForecast = async (g) => {
    setForecasts(f => {
      const existing = f[g.id] || {};
      return { ...f, [g.id]: { ...existing, open: !existing.open } };
    });
    const current = forecasts[g.id];
    if (current && current.data) return; // already loaded
    setForecasts(f => ({ ...f, [g.id]: { loading: true, open: true } }));
    try {
      const r = await axios.get(`${API}/goals/${g.id}/forecast`);
      setForecasts(f => ({ ...f, [g.id]: { data: r.data, loading: false, open: true } }));
    } catch (e) {
      setForecasts(f => ({ ...f, [g.id]: { error: 'Failed to load forecast', loading: false, open: true } }));
    }
  };

  const formatAdvice = (text) => {
    if(!text) return null;
    const lines = text.split(/\r?\n/).map(l=>l.trim()).filter(Boolean);
    const bullets = [];
    const paras = [];
    for (const l of lines) {
      if (/^[-*•]/.test(l) || /^\d+\./.test(l)) bullets.push(l.replace(/^[-*•\d.]+\s*/, ''));
      else paras.push(l);
    }
    return (
      <div className="text-sm space-y-2">
        {paras.map((p,i)=><p key={i}>{p}</p>)}
        {bullets.length>0 && <ul className="list-disc pl-5 space-y-1">{bullets.map((b,i)=><li key={i}>{b}</li>)}</ul>}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-4 rounded shadow space-y-2 max-w-md">
        <h2 className="font-semibold">Create Goal</h2>
        <input className="border p-2 w-full" placeholder="Name" value={form.name} onChange={e=>setForm(f=>({...f, name:e.target.value}))} />
        <input className="border p-2 w-full" type="number" placeholder="Target Amount" value={form.target_amount} onChange={e=>setForm(f=>({...f, target_amount:e.target.value}))} />
        <input className="border p-2 w-full" type="date" value={form.target_date} onChange={e=>setForm(f=>({...f, target_date:e.target.value}))} />
        <button className="bg-indigo-600 text-white px-4 py-2 rounded" onClick={create}>Add</button>
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        {goals.map(g => (
          <div key={g.id} className="bg-white p-4 rounded shadow space-y-2">
            <div className="flex justify-between items-center">
              <h3 className="font-semibold">{g.name}</h3>
              <button className="text-red-500 text-sm" onClick={()=>remove(g.id)}>Delete</button>
            </div>
            <div className="text-sm text-gray-600">Target: ${g.target_amount}</div>
            {g.target_date && <div className="text-xs text-gray-500">Target Date: {g.target_date}</div>}
            <ProgressBar percent={g.progress_percent} />
            <div className="flex gap-2 text-sm flex-wrap">
              <button className="bg-gray-200 px-2 py-1 rounded" onClick={()=>update(g.id,{current_amount: (g.current_amount || 0)+100})}>+100</button>
              <button className="bg-gray-200 px-2 py-1 rounded" onClick={()=>update(g.id,{current_amount: (g.current_amount || 0)+500})}>+500</button>
              <button className="bg-gray-200 px-2 py-1 rounded" onClick={()=>axios.post(`${API}/goals/${g.id}/sync`).then(load)}>Sync</button>
              <button className="bg-indigo-100 text-indigo-700 px-2 py-1 rounded" onClick={()=>toggleForecast(g)}>Forecast</button>
            </div>
            <div className="text-xs text-gray-500">Progress: {g.current_amount} / {g.target_amount} (${Math.round(g.progress_percent)}%)</div>
            {forecasts[g.id]?.open && (
              <div className="mt-2 border-t pt-2 space-y-2">
                {forecasts[g.id].loading && <div className="text-xs text-gray-500">Loading forecast...</div>}
                {forecasts[g.id].error && <div className="text-xs text-red-600">{forecasts[g.id].error}</div>}
                {forecasts[g.id].data && <ForecastCard f={forecasts[g.id].data} formatAdvice={formatAdvice} />}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ProgressBar({ percent }) {
  return (
    <div className="w-full h-3 bg-gray-200 rounded">
      <div className="h-3 bg-green-500 rounded" style={{ width: `${percent}%` }} />
    </div>
  );
}

function ForecastCard({ f, formatAdvice }) {
  const trackColor = f.on_track ? 'text-green-600' : 'text-amber-600';
  return (
    <div className="bg-gray-50 rounded p-3 space-y-2 text-xs border">
      <div className="flex flex-wrap gap-4">
        <Metric label="On Track" value={f.on_track === null ? 'N/A' : (f.on_track ? 'Yes' : 'No')} className={trackColor} />
        <Metric label="Req Monthly" value={f.required_monthly != null ? `$${f.required_monthly.toFixed(2)}` : 'N/A'} />
        <Metric label="Avg Monthly Net" value={`$${f.projected_monthly_savings.toFixed(2)}`} />
        <Metric label="Projected" value={f.projected_amount_by_target != null ? `$${f.projected_amount_by_target.toFixed(2)}` : 'N/A'} />
        <Metric label="Shortfall" value={f.shortfall != null ? `$${f.shortfall.toFixed(2)}` : 'N/A'} />
        <Metric label="Months Left" value={f.months_remaining != null ? f.months_remaining.toFixed(1) : 'N/A'} />
      </div>
      <div className="border rounded bg-white p-2">
        <div className="font-semibold mb-1">AI Suggestions</div>
        {formatAdvice(f.advice)}
      </div>
    </div>
  );
}

function Metric({ label, value, className='' }) {
  return (
    <div className="space-y-0.5 min-w-[90px]">
      <div className="uppercase tracking-wide text-[10px] text-gray-500">{label}</div>
      <div className={`font-medium text-xs ${className}`}>{value}</div>
    </div>
  );
}
