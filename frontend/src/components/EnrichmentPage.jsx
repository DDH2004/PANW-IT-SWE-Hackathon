import React, { useState, useEffect } from 'react';
import axios from 'axios';

/* EnrichmentPage
   Provides UI to trigger model-based categorization (/enrich) with promotion controls
   and view the latest enriched transaction category records.
*/
export default function EnrichmentPage({ API }) {
  const [limit, setLimit] = useState(50);
  const [model, setModel] = useState('phi3:mini');
  const [promote, setPromote] = useState(true);
  const [threshold, setThreshold] = useState(0.8);
  const [overwriteExisting, setOverwriteExisting] = useState(false);
  const [onlyUncategorized, setOnlyUncategorized] = useState(true);
  const [includeAlreadyEnriched, setIncludeAlreadyEnriched] = useState(false);
  // Cluster mode state
  const [clusterMode, setClusterMode] = useState(false);
  const [clusterThreshold, setClusterThreshold] = useState(0.5);
  const [clusterMinSize, setClusterMinSize] = useState(2);
  const [clusterMaxTokens, setClusterMaxTokens] = useState(2);
  const [running, setRunning] = useState(false);
  const [renameOld, setRenameOld] = useState('');
  const [renameNew, setRenameNew] = useState('');
  const [renaming, setRenaming] = useState(false);
  const [renameMsg, setRenameMsg] = useState('');
  const [result, setResult] = useState(null);
  const [latest, setLatest] = useState([]);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const fetchLatest = async () => {
    setRefreshing(true);
    try {
      const r = await axios.get(`${API}/enrich/latest?limit=25`);
      setLatest(r.data);
    } catch (e) {
      setError('Failed to load latest enrichment records');
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchLatest(); }, [API]);

  const runEnrichment = async () => {
    setRunning(true);
    setError('');
    setResult(null);
    try {
    const r = await axios.post(`${API}/enrich`, null, {
        params: {
          limit,
          model: clusterMode ? undefined : model,
          promote,
          promotion_min_confidence: threshold,
          overwrite_existing: overwriteExisting,
          only_uncategorized: onlyUncategorized,
          include_already_enriched: includeAlreadyEnriched,
          cluster_mode: clusterMode,
          cluster_threshold: clusterThreshold,
          cluster_min_size: clusterMinSize,
          cluster_max_tokens: clusterMaxTokens,
        }
      });
  setResult(r.data);
      await fetchLatest();
    } catch (e) {
      setError('Enrichment failed');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-semibold">Model Categorization</h2>
        <p className="text-sm text-gray-600 max-w-2xl">Trigger model-based categorization for recent uncategorized transactions. High-confidence results can optionally promote directly into the primary transaction category field.</p>
      </div>
      <div className="bg-white shadow rounded p-4 space-y-4">
        <div className="grid md:grid-cols-3 gap-4">
          <NumberField label="Limit" value={limit} setValue={setLimit} min={1} max={500} step={10} />
          <div className="space-y-1">
            <label className="text-xs uppercase tracking-wide text-gray-500 font-medium">Model</label>
            <input className={`border rounded px-2 py-1 w-full ${clusterMode? 'bg-gray-100 cursor-not-allowed':''}`} value={model} disabled={clusterMode} onChange={e=>setModel(e.target.value)} placeholder="model name" />
          </div>
          <div className="space-y-1">
            <label className="text-xs uppercase tracking-wide text-gray-500 font-medium">Promotion Threshold</label>
            <input type="number" min={0} max={1} step={0.01} className="border rounded px-2 py-1 w-full" value={threshold} onChange={e=>setThreshold(parseFloat(e.target.value)||0)} />
          </div>
        </div>
        <ParamDescriptions clusterMode={clusterMode} />
        <div className="flex flex-wrap gap-6">
          <Checkbox label="Promote Categories" checked={promote} onChange={setPromote} />
          <Checkbox label="Overwrite Existing" checked={overwriteExisting} onChange={setOverwriteExisting} disabled={!promote} />
          <Checkbox label="Only Uncategorized" checked={onlyUncategorized} onChange={setOnlyUncategorized} />
          <Checkbox label="Include Already Enriched" checked={includeAlreadyEnriched} onChange={setIncludeAlreadyEnriched} disabled={onlyUncategorized && !overwriteExisting} />
          <Checkbox label="Cluster Mode" checked={clusterMode} onChange={setClusterMode} />
        </div>
        {clusterMode && (
          <div className="grid md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <label className="text-xs uppercase tracking-wide text-gray-500 font-medium">Cluster Threshold</label>
              <input type="number" min={0} max={1} step={0.01} className="border rounded px-2 py-1 w-full" value={clusterThreshold} onChange={e=>setClusterThreshold(parseFloat(e.target.value)||0)} />
            </div>
            <NumberField label="Min Size" value={clusterMinSize} setValue={setClusterMinSize} min={2} max={20} step={1} />
            <NumberField label="Max Tokens" value={clusterMaxTokens} setValue={setClusterMaxTokens} min={1} max={5} step={1} />
            <div className="space-y-1 text-xs text-gray-500 flex items-end pb-1">Groups similar descriptions into emergent labels; model param ignored.</div>
          </div>
        )}
    <div className="flex flex-wrap items-center gap-3">
            <button disabled={running} onClick={runEnrichment} className={`px-4 py-2 rounded text-white ${running? 'bg-indigo-400 cursor-wait':'bg-indigo-600 hover:bg-indigo-700'}`}>{running? 'Running...':'Run Enrichment'}</button>
            <button onClick={fetchLatest} disabled={refreshing} className="px-3 py-2 text-sm rounded bg-gray-100 hover:bg-gray-200">{refreshing? 'Refreshing...':'Refresh Latest'}</button>
      {result && (
        <span className="text-sm text-gray-700 flex flex-col gap-0.5">
          {!result.cluster_mode && (
            <>
              <span>Candidates: <strong>{result.candidates ?? '—'}</strong> | Enriched: <strong>{result.enriched}</strong> | Promoted: <strong>{result.promoted_count}</strong> (threshold {result.threshold})</span>
              {(result.reason || result.only_uncategorized !== undefined) && (
                <span className="text-xs text-gray-500">Flags: only_uncategorized={String(result.only_uncategorized)} include_already_enriched={String(result.include_already_enriched)}{result.reason? ` • ${result.reason}`:''}</span>
              )}
            </>
          )}
          {result.cluster_mode && (
            <>
              <span>Cluster Mode: <strong>{result.clusters?.length || 0}</strong> clusters | Candidates: <strong>{result.candidates}</strong> | Assigned: <strong>{result.enriched}</strong></span>
              <span className="text-xs text-gray-500">cluster_threshold={clusterThreshold} min_size={clusterMinSize} max_tokens={clusterMaxTokens}</span>
            </>
          )}
        </span>
      )}
        </div>
        {error && <div className="text-sm text-red-600">{error}</div>}
      </div>
      {result?.cluster_mode && result?.clusters?.length > 0 && (
        <div>
          <h3 className="font-semibold mb-2">Clusters (latest run)</h3>
          <div className="overflow-auto border rounded">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-2 py-1 text-left">Label</th>
                  <th className="px-2 py-1 text-left">Size</th>
                  <th className="px-2 py-1 text-left">Avg Similarity</th>
                  <th className="px-2 py-1 text-left">Sample Members (prev category → description)</th>
                </tr>
              </thead>
              <tbody>
                {result.clusters.map(c => {
                  const sample = (c.members || []).slice(0,4);
                  return (
                    <tr key={c.label} className="odd:bg-white even:bg-gray-50 align-top">
                      <td className="px-2 py-1 font-mono text-xs break-all">{c.label}</td>
                      <td className="px-2 py-1">{c.size}</td>
                      <td className="px-2 py-1">{c.avg_similarity?.toFixed ? c.avg_similarity.toFixed(2): c.avg_similarity}</td>
                      <td className="px-2 py-1 text-[10px] space-y-1">
                        {sample.map(m => (
                          <div key={m.transaction_id} className="truncate" title={`${m.previous_category || '∅'} → ${m.description}`}>{m.previous_category || '∅'} → {m.description.slice(0,80)}{m.description.length>80?'…':''}</div>
                        ))}
                        {c.members?.length > sample.length && (
                          <div className="text-gray-400">+{c.members.length - sample.length} more…</div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="mt-4 p-3 border rounded bg-gray-50 space-y-2">
            <h4 className="font-semibold text-sm">Rename Cluster</h4>
            <div className="grid md:grid-cols-5 gap-2 items-end">
              <div className="md:col-span-2 space-y-1">
                <label className="text-xs uppercase tracking-wide text-gray-500 font-medium">Old Label</label>
                <input className="border rounded px-2 py-1 w-full" value={renameOld} onChange={e=>setRenameOld(e.target.value)} placeholder="Cluster: token_token" />
              </div>
              <div className="md:col-span-2 space-y-1">
                <label className="text-xs uppercase tracking-wide text-gray-500 font-medium">New Label</label>
                <input className="border rounded px-2 py-1 w-full" value={renameNew} onChange={e=>setRenameNew(e.target.value)} placeholder="New descriptive label" />
              </div>
              <div className="flex gap-2">
                <button disabled={renaming || !renameOld || !renameNew} onClick={async ()=>{
                  setRenaming(true); setRenameMsg('');
                  try { const r = await axios.post(`${API}/enrich/rename_cluster`, { old_label: renameOld, new_label: renameNew }); setRenameMsg(`Renamed ${r.data.updated_transactions} tx / ${r.data.updated_history_rows} history rows.`); setRenameOld(''); setRenameNew(''); fetchLatest(); } catch(e){ setRenameMsg('Rename failed'); } finally { setRenaming(false);} }} className={`px-3 py-2 text-xs rounded text-white ${renaming? 'bg-indigo-400 cursor-wait':'bg-indigo-600 hover:bg-indigo-700'}`}>{renaming? 'Renaming...':'Apply'}</button>
                <button disabled={renaming} onClick={()=>{setRenameOld(''); setRenameNew(''); setRenameMsg('');}} className="px-3 py-2 text-xs rounded border">Clear</button>
              </div>
            </div>
            {renameMsg && <div className="text-xs text-gray-600">{renameMsg}</div>}
            <p className="text-xs text-gray-500 leading-snug">Renaming updates current transaction categories (if they match old label) and historical cluster rows so future analytics stay consistent.</p>
          </div>
        </div>
      )}
      <div>
        <h3 className="font-semibold mb-2">Latest Enriched Records</h3>
        <div className="overflow-auto border rounded">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-2 py-1 text-left">Txn ID</th>
                <th className="px-2 py-1 text-left">Category</th>
                <th className="px-2 py-1 text-left">Confidence</th>
                <th className="px-2 py-1 text-left">Model</th>
                <th className="px-2 py-1 text-left">Created</th>
                <th className="px-2 py-1 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {latest.map(r => (
                <tr key={r.transaction_id} className={`odd:bg-white even:bg-gray-50 ${r.promoted? 'border-l-4 border-green-500':''}`}>
                  <td className="px-2 py-1 font-mono text-xs">{r.transaction_id}</td>
                  <td className="px-2 py-1 flex items-center gap-2">
                    {r.category}
                    {r.promoted && <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-semibold">PROMOTED</span>}
                  </td>
                  <td className="px-2 py-1">{r.confidence?.toFixed ? r.confidence.toFixed(2): r.confidence}</td>
                  <td className="px-2 py-1 text-xs text-gray-600">{r.model}</td>
                  <td className="px-2 py-1 text-xs text-gray-500">{r.created_at?.replace('T',' ').split('.')[0]}</td>
                  <td className="px-2 py-1 text-xs">
                    {r.promoted ? (
                      <RevertButton API={API} txnId={r.transaction_id} onDone={fetchLatest} />
                    ) : <span className="text-gray-400">—</span>}
                  </td>
                </tr>
              ))}
              {latest.length === 0 && <tr><td className="px-2 py-4 text-center text-gray-500" colSpan={6}>No enrichment records yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function NumberField({ label, value, setValue, min, max, step }) {
  return (
    <div className="space-y-1">
      <label className="text-xs uppercase tracking-wide text-gray-500 font-medium">{label}</label>
      <input type="number" className="border rounded px-2 py-1 w-full" value={value} min={min} max={max} step={step}
        onChange={e=>setValue(parseInt(e.target.value)||0)} />
    </div>
  );
}

function ParamDescriptions({ clusterMode }) {
  return (
    <div className="text-xs text-gray-500 space-y-1">
      {!clusterMode && (
        <p><strong>Model Mode:</strong> Uses heuristic/LLM-like keyword matcher to map each transaction into a fixed category set; promotion writes high-confidence categories back.</p>
      )}
      {clusterMode && (
        <>
          <p><strong>Cluster Mode:</strong> Groups transactions by shared tokens (Jaccard similarity). Label is auto-derived from most frequent tokens. Adjust parameters below:</p>
          <ul className="list-disc ml-5 space-y-0.5">
            <li><strong>Cluster Threshold:</strong> Minimum Jaccard similarity for a transaction to join a seed cluster (higher = tighter, fewer clusters).</li>
            <li><strong>Min Size:</strong> Clusters smaller than this are ignored (their members receive no cluster record).</li>
            <li><strong>Max Tokens:</strong> Number of top frequent tokens used to build the emergent cluster label.</li>
          </ul>
        </>
      )}
    </div>
  );
}

function Checkbox({ label, checked, onChange, disabled }) {
  return (
    <label className={`flex items-center gap-2 text-sm ${disabled? 'opacity-50':''}`}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={e=>onChange(e.target.checked)} />
      {label}
    </label>
  );
}

function RevertButton({ API, txnId, onDone }) {
  const [busy, setBusy] = useState(false);
  const revert = async () => {
    setBusy(true);
    try {
      await axios.patch(`${API}/transactions/${txnId}/category`, { category: null });
    } catch (e) {
      // swallow
    } finally {
      setBusy(false);
      onDone && onDone();
    }
  };
  return <button disabled={busy} onClick={revert} className={`px-2 py-1 rounded border text-[10px] font-medium ${busy? 'opacity-50 cursor-wait':'hover:bg-gray-50'}`}>{busy? 'Reverting...':'Revert'}</button>;
}
