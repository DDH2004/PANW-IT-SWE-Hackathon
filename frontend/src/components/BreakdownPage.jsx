import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function BreakdownPage({ API }) {
  const [categories, setCategories] = useState(null);
  const [merchants, setMerchants] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [c,m,t] = await Promise.all([
        axios.get(`${API}/breakdown/categories?months=3`),
        axios.get(`${API}/breakdown/merchants?limit=15`),
        axios.get(`${API}/breakdown/timeline?months=6`)
      ]);
      setCategories(c.data);
      setMerchants(m.data);
      setTimeline(t.data);
    } catch (e) {
      setError('Failed to load breakdown');
    } finally {
      setLoading(false);
    }
  };

  useEffect(()=>{ load(); }, [API]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div className="text-red-600 text-sm">{error}</div>;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Itemized Breakdown</h2>
        <button onClick={load} className="text-sm px-3 py-1 rounded bg-gray-100 hover:bg-gray-200">Refresh</button>
      </div>
      <CategorySection data={categories} />
      <MerchantSection data={merchants} />
      <TimelineSection data={timeline} />
    </div>
  );
}

function CategorySection({ data }) {
  if (!data) return null;
  return (
    <div className="space-y-3">
      <h3 className="font-medium">By Category (last {data.months} months)</h3>
      <div className="overflow-auto border rounded">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-2 py-1 text-left">Category</th>
              <th className="px-2 py-1 text-right">Spend</th>
              <th className="px-2 py-1 text-right">Income</th>
              <th className="px-2 py-1 text-right">Net</th>
              <th className="px-2 py-1 text-right">Spend %</th>
            </tr>
          </thead>
          <tbody>
            {data.categories.map(c => (
              <tr key={c.category} className="odd:bg-white even:bg-gray-50">
                <td className="px-2 py-1">{c.category}</td>
                <td className="px-2 py-1 text-right">${c.spend.toFixed(2)}</td>
                <td className="px-2 py-1 text-right">${c.income.toFixed(2)}</td>
                <td className={`px-2 py-1 text-right ${c.net < 0 ? 'text-red-600':'text-green-600'}`}>${c.net.toFixed(2)}</td>
                <td className="px-2 py-1 text-right">{c.share_of_spend.toFixed(2)}%</td>
              </tr>
            ))}
            {data.categories.length === 0 && <tr><td className="px-2 py-4 text-center text-gray-500" colSpan={5}>No data</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MerchantSection({ data }) {
  if (!data) return null;
  return (
    <div className="space-y-3">
      <h3 className="font-medium">Top Merchants by Spend</h3>
      <div className="overflow-auto border rounded">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-2 py-1 text-left">Merchant</th>
              <th className="px-2 py-1 text-right">Transactions</th>
              <th className="px-2 py-1 text-right">Spend</th>
              <th className="px-2 py-1 text-right">Income</th>
              <th className="px-2 py-1 text-right">Net</th>
            </tr>
          </thead>
          <tbody>
            {data.merchants.map(m => (
              <tr key={m.merchant} className="odd:bg-white even:bg-gray-50">
                <td className="px-2 py-1">{m.merchant}</td>
                <td className="px-2 py-1 text-right">{m.transactions}</td>
                <td className="px-2 py-1 text-right">${m.spend.toFixed(2)}</td>
                <td className="px-2 py-1 text-right">${m.income.toFixed(2)}</td>
                <td className={`px-2 py-1 text-right ${m.net < 0 ? 'text-red-600':'text-green-600'}`}>${m.net.toFixed(2)}</td>
              </tr>
            ))}
            {data.merchants.length === 0 && <tr><td className="px-2 py-4 text-center text-gray-500" colSpan={5}>No data</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TimelineSection({ data }) {
  if (!data) return null;
  return (
    <div className="space-y-3">
      <h3 className="font-medium">Monthly Timeline (last {data.months} months)</h3>
      <div className="overflow-auto border rounded">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-2 py-1 text-left">Month</th>
              <th className="px-2 py-1 text-right">Income</th>
              <th className="px-2 py-1 text-right">Spend</th>
              <th className="px-2 py-1 text-right">Net</th>
            </tr>
          </thead>
          <tbody>
            {data.timeline.map(p => (
              <tr key={p.month} className="odd:bg-white even:bg-gray-50">
                <td className="px-2 py-1">{p.month}</td>
                <td className="px-2 py-1 text-right">${p.income.toFixed(2)}</td>
                <td className="px-2 py-1 text-right">${p.spend.toFixed(2)}</td>
                <td className={`px-2 py-1 text-right ${p.net < 0 ? 'text-red-600':'text-green-600'}`}>${p.net.toFixed(2)}</td>
              </tr>
            ))}
            {data.timeline.length === 0 && <tr><td className="px-2 py-4 text-center text-gray-500" colSpan={4}>No data</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
