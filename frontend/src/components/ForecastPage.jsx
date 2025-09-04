import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart, Legend } from 'recharts';

export default function ForecastPage({ API }) {
  const [method, setMethod] = useState('auto');
  const [horizon, setHorizon] = useState(90);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true); setError('');
    try {
      const r = await axios.get(`${API}/forecast`, { params: { method, horizon_days: horizon }});
      setData(r.data);
    } catch(e) {
      setError(e.response?.data?.detail || 'Failed to fetch forecast');
    } finally { setLoading(false); }
  };

  useEffect(()=>{ load(); /* eslint-disable-next-line */ }, []);
  useEffect(()=>{ load(); /* eslint-disable-next-line */ }, [method, horizon]);

  const daily = (data?.daily_forecast || []).map(d => ({
    date: d.date,
    predicted: d.predicted_spend,
    lower: d.lower ?? d.predicted_spend,
    upper: d.upper ?? d.predicted_spend,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Method</label>
          <select value={method} onChange={e=>setMethod(e.target.value)} className="border rounded px-2 py-1 text-sm">
            <option value="auto">Auto</option>
            <option value="prophet">Prophet</option>
            <option value="simple">Simple</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Horizon (days)</label>
          <input type="number" min={14} max={365} value={horizon} onChange={e=>setHorizon(Number(e.target.value)||90)} className="border rounded px-2 py-1 w-24 text-sm" />
        </div>
        <button onClick={load} disabled={loading} className="self-start mt-4 text-sm px-3 py-1 rounded bg-indigo-600 text-white disabled:bg-indigo-400">{loading? 'Loading...':'Refresh'}</button>
        {data && (
          <div className="ml-auto flex flex-wrap gap-6 text-xs bg-white p-3 rounded shadow">
            <Stat label="Method" value={data.forecast_method || 'n/a'} />
            <Stat label="Annual (heuristic)" value={`$${Math.round(data.annual_spend_projection)}`} />
            {data.next_30d_spend !== undefined && <Stat label="Next 30d" value={`$${data.next_30d_spend}`} />}
            {data.next_60d_spend !== undefined && <Stat label="Next 60d" value={`$${data.next_60d_spend}`} />}
            {data.next_90d_spend !== undefined && <Stat label="Next 90d" value={`$${data.next_90d_spend}`} />}
          </div>
        )}
      </div>
      {error && <div className="text-sm text-red-600">{error}</div>}
      <div className="bg-white p-4 rounded shadow">
        <h2 className="font-semibold mb-2">Daily Spend Forecast</h2>
        {!loading && daily.length === 0 && <div className="text-xs text-gray-500">No forecast data.</div>}
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={daily} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <defs>
                <linearGradient id="fcFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.35}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 10 }} hide={daily.length > 60} />
              <YAxis tick={{ fontSize: 10 }} width={60} />
              <Tooltip formatter={(v)=>`$${v}`} />
              <Legend />
              {daily.some(d=>d.upper !== d.lower) && (
                <>
                  <Line type="monotone" dataKey="upper" stroke="#94a3b8" strokeDasharray="4 4" dot={false} name="Upper" />
                  <Line type="monotone" dataKey="lower" stroke="#94a3b8" strokeDasharray="4 4" dot={false} name="Lower" />
                </>
              )}
              <Area type="monotone" dataKey="predicted" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#fcFill)" name="Predicted" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        {data?.reason && <p className="mt-2 text-[11px] text-gray-500">Note: {data.reason.replace(/_/g,' ')}</p>}
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-gray-500">{label}</span>
      <span className="font-semibold text-gray-800">{value}</span>
    </div>
  );
}
