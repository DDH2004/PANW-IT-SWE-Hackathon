import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function AnomaliesPage({ API }) {
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [actionState, setActionState] = useState({loading:false,message:''});
  const [confirm, setConfirm] = useState(null); // {keepOne:boolean}
  const fetchData = () => axios.get(`${API}/anomalies`).then(r=>setData(r.data));
  useEffect(()=>{ fetchData(); }, [API]);
  if(!data) return <div>Loading...</div>;

  const toggleTxn = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleGroup = (group) => {
    const ids = group.transactions.map(t=>t.id);
    const allSelected = ids.every(id=>selectedIds.has(id));
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (allSelected) ids.forEach(id=> next.delete(id)); else ids.forEach(id=> next.add(id));
      return next;
    });
  };

  const performDelete = async (keepOne=false) => {
    if(selectedIds.size === 0) return;
    setActionState(s=>({...s,loading:true,message:'Processing...'}));
    try {
      const payload = { transaction_ids: Array.from(selectedIds), validate_duplicates: true, keep_one_per_group: keepOne };
      const r = await axios.post(`${API}/anomalies/dedupe`, payload);
      setActionState({loading:false,message:`Deleted ${r.data.deleted_count}.`});
      setSelectedIds(new Set());
      fetchData();
    } catch (e) {
      setActionState({loading:false,message:'Error: ' + (e.response?.data?.detail || 'failed')});
    } finally {
      setConfirm(null);
    }
  };

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
      <div className="bg-white p-4 rounded shadow space-y-3">
        <div className="flex items-center gap-3">
          <h2 className="font-semibold">Possible Duplicates</h2>
          {selectedIds.size > 0 && (
            <div className="flex gap-2 text-xs">
              <button disabled={actionState.loading} onClick={()=>setConfirm({keepOne:false})} className="px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-50">Delete Selected</button>
              <button disabled={actionState.loading} onClick={()=>setConfirm({keepOne:true})} className="px-2 py-1 rounded bg-orange-600 text-white hover:bg-orange-700 disabled:opacity-50">Delete (Keep 1 / Group)</button>
            </div>
          )}
          {actionState.message && <span className="text-xs text-gray-600">{actionState.message}</span>}
        </div>
        {data.duplicates.length === 0 && <div className="text-sm text-gray-500">None detected</div>}
        <ul className="text-sm divide-y">
          {data.duplicates.map((group,i)=>{
            const groupSelectedCount = group.transactions.filter(t=>selectedIds.has(t.id)).length;
            return (
              <li key={i} className="py-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button type="button" onClick={() => setExpanded(e=>({...e,[i]:!e[i]}))} className="text-xs px-1 py-0.5 rounded border">
                      {expanded[i] ? '−' : '+'}
                    </button>
                    <input type="checkbox" checked={group.transactions.every(t=>selectedIds.has(t.id))} onChange={()=>toggleGroup(group)} />
                    <span className="font-medium">{group.date} · {group.merchant || '—'} · {group.category || '—'}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-red-600">${Math.abs(group.amount)}</span>
                    <span className="text-[11px] text-gray-500">x{group.count}{groupSelectedCount? ` (${groupSelectedCount} selected)` : ''}</span>
                  </div>
                </div>
                {expanded[i] && (
                  <table className="mt-2 w-full text-[11px]">
                    <thead>
                      <tr className="text-gray-500 text-left">
                        <th className="pr-2">Sel</th>
                        <th>Description</th>
                        <th>Amount</th>
                        <th>Merchant</th>
                        <th>Category</th>
                        <th>ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.transactions.map(tx => (
                        <tr key={tx.id} className="odd:bg-gray-50">
                          <td><input type="checkbox" checked={selectedIds.has(tx.id)} onChange={()=>toggleTxn(tx.id)} /></td>
                          <td className="pr-2 truncate max-w-xs" title={tx.description}>{tx.description}</td>
                          <td>{tx.amount.toFixed(2)}</td>
                          <td>{tx.merchant || '—'}</td>
                          <td>{tx.category || '—'}</td>
                          <td className="text-gray-500 font-mono">{tx.id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </li>
            );
          })}
        </ul>
  <p className="text-[10px] text-gray-500 pt-1">Deletion is permanent.</p>
      </div>
      {confirm && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded shadow-lg p-4 w-full max-w-sm space-y-3">
            <h3 className="font-semibold text-sm">Confirm deletion</h3>
            <p className="text-xs text-gray-600">You are about to delete {selectedIds.size} transaction(s){confirm.keepOne && ' (keeping earliest per duplicate group if all selected)'}. They will be archived for a short time so you can undo.</p>
            <div className="flex justify-end gap-2 text-xs">
              <button onClick={()=>setConfirm(null)} className="px-2 py-1 rounded border">Cancel</button>
              <button onClick={()=>performDelete(confirm.keepOne)} disabled={actionState.loading} className="px-3 py-1 rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-50">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
