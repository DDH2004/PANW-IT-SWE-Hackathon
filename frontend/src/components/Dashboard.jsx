import React, { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#3b82f6', '#8b5cf6'];

export default function Dashboard({ API }) {
  const [transactions, setTransactions] = useState([]);
  const [insights, setInsights] = useState({ spending_by_category: [], total_spend: 0, total_income: 0, net: 0 });
  const [kpis, setKpis] = useState(null);
  const [timeframe, setTimeframe] = useState('all'); // '1m' | '1y' | 'all'

  useEffect(() => {
    axios.get(`${API}/transactions`).then(r => setTransactions(r.data));
    axios.get(`${API}/insights`).then(r => setInsights(r.data));
  axios.get(`${API}/dashboard`).then(r => setKpis(r.data));
  }, [API]);

  // Compute date threshold based on timeframe
  const now = useMemo(() => new Date(), []);
  const threshold = useMemo(() => {
    if (timeframe === '1m') {
      const d = new Date(now); d.setDate(d.getDate() - 30); return d;
    }
    if (timeframe === '1y') {
      const d = new Date(now); d.setFullYear(d.getFullYear() - 1); return d;
    }
    return null; // all time
  }, [timeframe, now]);

  // Filtered transactions for charts
  const filteredTxns = useMemo(() => {
    if (!threshold) return transactions;
    return transactions.filter(t => {
      const d = new Date(t.date);
      return d >= threshold;
    });
  }, [transactions, threshold]);

  // Recompute category aggregation if timeframe != all
  const categoryData = useMemo(() => {
    if (timeframe === 'all') return insights.spending_by_category || [];
    const agg = {};
    for (const t of filteredTxns) {
      if (t.amount < 0) {
        const cat = t.category || 'Uncategorized';
        agg[cat] = (agg[cat] || 0) + (-t.amount);
      }
    }
    return Object.entries(agg)
      .map(([category, total]) => ({ category, total: Number(total.toFixed(2)) }))
      .sort((a,b) => b.total - a.total);
  }, [filteredTxns, insights.spending_by_category, timeframe]);

  const lineData = useMemo(() => filteredTxns
    .filter(t => t.amount < 0)
    .slice()
    .reverse()
    .map(t => ({ date: t.date, amount: -t.amount })), [filteredTxns]);

  // Active category for legend & slice hover highlight
  const [activeCategory, setActiveCategory] = useState(null);

  const renderLegend = (props) => {
    const { payload } = props;
    if (!payload) return null;
    return (
      <ul className="flex flex-wrap gap-3 text-[11px] mt-2">
        {payload.map((entry, idx) => {
          const cat = entry.value;
          const isActive = activeCategory === cat;
          return (
            <li
              key={`legend-${idx}`}
              onMouseEnter={() => setActiveCategory(cat)}
              onMouseLeave={() => setActiveCategory(null)}
              className={`flex items-center gap-1 cursor-pointer select-none px-1 py-0.5 rounded ${isActive ? 'bg-indigo-50 ring-1 ring-indigo-300' : 'hover:bg-gray-50'}`}
            >
              <span className="w-3 h-3 rounded-sm" style={{ background: entry.color }} />
              <span className={`truncate max-w-[120px] ${isActive ? 'font-semibold text-gray-800' : 'text-gray-600'}`}>{cat}</span>
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <div className="grid md:grid-cols-2 gap-8">
      <div className="md:col-span-2 flex gap-3 items-center mb-2 flex-wrap">
        <span className="text-xs font-semibold tracking-wide text-gray-600">TIMEFRAME:</span>
        {['1m','1y','all'].map(tf => (
          <button
            key={tf}
            onClick={() => setTimeframe(tf)}
            className={`text-xs px-3 py-1 rounded border ${timeframe===tf ? 'bg-indigo-600 text-white border-indigo-600':'bg-white text-gray-700 border-gray-300 hover:border-indigo-400'}`}
          >{tf === '1m' ? 'Past 1M' : tf === '1y' ? 'Past 1Y' : 'All Time'}</button>
        ))}
        {threshold && (
          <span className="ml-auto text-[10px] text-gray-500">Showing from {threshold.toISOString().slice(0,10)}</span>
        )}
      </div>
  <div className="bg-white p-4 rounded shadow">
        <h2 className="font-semibold mb-2">Spending by Category</h2>
        <ResponsiveContainer width="100%" height={340}>
          <PieChart margin={{ top: 4, right: 8, left: 8, bottom: 12 }}>
            <Pie
              data={categoryData}
              dataKey="total"
              nameKey="category"
              innerRadius={40}
              outerRadius={110}
              onMouseLeave={() => setActiveCategory(null)}
            >
              {categoryData.map((d, i) => {
                const isDimmed = activeCategory && activeCategory !== d.category;
                const isActive = activeCategory && activeCategory === d.category;
                return (
                  <Cell
                    key={d.category}
                    fill={COLORS[i % COLORS.length]}
                    stroke={isActive ? '#111827' : '#fff'}
                    strokeWidth={isActive ? 2 : 1}
                    style={{
                      opacity: isDimmed ? 0.35 : 1,
                      transition: 'opacity 160ms, stroke-width 160ms'
                    }}
                    onMouseEnter={() => setActiveCategory(d.category)}
                  />
                );
              })}
            </Pie>
            <Tooltip formatter={(val,name)=>[`$${val}`, name]} />
            <Legend verticalAlign="bottom" align="center" content={renderLegend} />
          </PieChart>
        </ResponsiveContainer>
      </div>
  <div className="bg-white p-4 rounded shadow">
        <h2 className="font-semibold mb-2">Transaction Trend</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={lineData}>
            <XAxis dataKey="date" hide />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="amount" stroke="#6366f1" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="bg-white p-4 rounded shadow md:col-span-2 flex flex-wrap gap-6">
        <div><span className="text-sm text-gray-500">Total Income</span><div className="text-lg font-semibold">${insights.total_income}</div></div>
        <div><span className="text-sm text-gray-500">Total Spend</span><div className="text-lg font-semibold">${insights.total_spend}</div></div>
        <div><span className="text-sm text-gray-500">Net</span><div className={`text-lg font-semibold ${insights.net >=0 ? 'text-green-600':'text-red-600'}`}>${insights.net}</div></div>
        {kpis && (
          <>
            <div><span className="text-sm text-gray-500">MTD Spend</span><div className="text-lg font-semibold">${kpis.mtd_spend}</div></div>
            <div><span className="text-sm text-gray-500">Savings Rate</span><div className="text-lg font-semibold">{kpis.savings_rate_pct}%</div></div>
            {kpis.monthly_budget && (
              <div><span className="text-sm text-gray-500">Budget Used</span><div className="text-lg font-semibold">{kpis.budget_used_pct || 0}%</div></div>
            )}
          </>
        )}
      </div>
      {kpis && (
        <div className="bg-white p-4 rounded shadow md:col-span-2">
          <h2 className="font-semibold mb-2">MoM Category Changes</h2>
          <ul className="space-y-1 text-sm">
            {kpis.mom_category_changes.map(c => (
              <li key={c.category} className="flex justify-between">
                <span>{c.category}</span>
                <span className={c.delta > 0 ? 'text-red-600' : 'text-green-600'}>
                  {c.delta > 0 ? '+' : ''}{c.delta} {c.delta_pct !== null && c.delta_pct !== undefined ? `(${c.delta_pct}%)` : ''}
                </span>
              </li>
            ))}
          </ul>
          <h2 className="font-semibold mt-4 mb-2">Largest Expenses (MTD)</h2>
          <ul className="space-y-1 text-sm">
            {kpis.largest_expenses.map((e,i) => (
              <li key={i} className="flex justify-between">
                <span>{e.description}</span><span className="text-red-600">${Math.abs(e.amount)}</span>
              </li>
            ))}
          </ul>
          {kpis.upcoming_subscriptions.length > 0 && (
            <>
              <h2 className="font-semibold mt-4 mb-2">Upcoming Subscriptions (14d)</h2>
              <ul className="space-y-1 text-sm">
                {kpis.upcoming_subscriptions.map((s,i)=>(
                  <li key={i} className="flex justify-between"><span>{s.merchant}</span><span>{s.next_estimate}</span></li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
