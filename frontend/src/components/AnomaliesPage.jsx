import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function AnomaliesPage({ API }) {
  const [data, setData] = useState(null);
  useEffect(()=>{ axios.get(`${API}/anomalies`).then(r=>setData(r.data)); }, [API]);
  if(!data) return <div>Loading...</div>;
  return (
    <div className="space-y-6">
      <div className="bg-white p-4 rounded shadow">
        <h2 className="font-semibold mb-2">Outlier Expenses</h2>
        {data.outliers.length === 0 && <div className="text-sm text-gray-500">None detected</div>}
        <ul className="text-sm space-y-1">
          {data.outliers.map((o,i)=>(
            <li key={i} className="flex justify-between">
              <span>{o.date} - {o.description}</span>
              <span className="text-red-600">${Math.abs(o.amount)}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="bg-white p-4 rounded shadow">
        <h2 className="font-semibold mb-2">Possible Duplicates</h2>
        {data.duplicates.length === 0 && <div className="text-sm text-gray-500">None detected</div>}
        <ul className="text-sm space-y-1">
          {data.duplicates.map((d,i)=>(
            <li key={i} className="flex justify-between">
              <span>{d.date} - {d.merchant} x{d.count}</span>
              <span className="text-red-600">${Math.abs(d.amount)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
