import React, { useState, useEffect } from 'react';
// Single axios import (removed accidental duplicate during merge)
import axios from 'axios';
import Dashboard from '../components/Dashboard';
import CoachChat from '../components/CoachChat';
import GoalsPage from '../components/GoalsPage';
import SettingsPage from '../components/SettingsPage';
import AnomaliesPage from '../components/AnomaliesPage';
import SubscriptionsPage from '../components/SubscriptionsPage';
import EnrichmentPage from '../components/EnrichmentPage';
import BreakdownPage from '../components/BreakdownPage';
import OnboardingOverlay from '../components/OnboardingOverlay';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  const [view, setView] = useState('dashboard');
  const [showOnboarding, setShowOnboarding] = useState(false);

  // decide whether to show onboarding on first mount
  useEffect(() => {
    try {
      const seen = localStorage.getItem('onboarding_seen_v1');
      // Show only if not seen yet
      if (!seen) {
        setShowOnboarding(true);
      }
    } catch (_) {/* ignore storage errors */}
  }, []);

  const dismissOnboarding = (persist=true) => {
    setShowOnboarding(false);
    if (persist) {
      try { localStorage.setItem('onboarding_seen_v1', '1'); } catch(_){}
    }
  };

  const jumpTo = (key) => {
    setView(key);
    dismissOnboarding();
  };
  const navOrder = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'upload', label: 'Upload' },
    { key: 'breakdown', label: 'Breakdown' },
    { key: 'enrichment', label: 'Enrichment' },
    { key: 'subscriptions', label: 'Subscriptions' },
    { key: 'goals', label: 'Goals' },
    { key: 'coach', label: 'Coach' },
    { key: 'anomalies', label: 'Anomalies' },
    { key: 'settings', label: 'Settings' },
  ];
  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-indigo-600 text-white p-4 flex flex-wrap gap-3 text-sm">
        {navOrder.map(item => (
          <button
            key={item.key}
            onClick={() => setView(item.key)}
            className={`px-2 py-1 rounded transition-colors ${view === item.key ? 'bg-white text-indigo-700 font-semibold shadow-sm' : 'hover:bg-indigo-500'}`}
          >{item.label}</button>
        ))}
        <button
          onClick={() => setShowOnboarding(true)}
          className="ml-auto px-2 py-1 rounded bg-indigo-500 hover:bg-indigo-400 text-white font-medium shadow-sm"
        >Guide</button>
      </nav>
      <main className="flex-1 p-6">
        {view === 'upload' && <UploadPage />}
        {view === 'dashboard' && <Dashboard API={API} />}
  {view === 'coach' && <CoachChat API={API} />}
  {view === 'goals' && <GoalsPage API={API} />}
  {view === 'settings' && <SettingsPage API={API} />}
  {view === 'anomalies' && <AnomaliesPage API={API} />}
  {view === 'subscriptions' && <SubscriptionsPage API={API} />}
  {view === 'enrichment' && <EnrichmentPage API={API} />}
  {view === 'breakdown' && <BreakdownPage API={API} />}
      </main>
      {showOnboarding && (
        <OnboardingOverlay
          onDismiss={() => dismissOnboarding(true)}
          onAction={(key) => jumpTo(key)}
        />
      )}
    </div>
  );
}

function UploadPage() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');
  const [needsConfirm, setNeedsConfirm] = useState(false);
  const [candidates, setCandidates] = useState([]);
  const [suggested, setSuggested] = useState(null);
  const [chosen, setChosen] = useState('');
  const [autoConfirm, setAutoConfirm] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [lastRaw, setLastRaw] = useState(null);
  const [showDebug, setShowDebug] = useState(false);
  const [forceSelection, setForceSelection] = useState(false);

  const submit = async (overrideParams={}, {analyzeOnly=false} = {}) => {
    if(!file) return;
    setUploading(true);
    setStatus(analyzeOnly? 'Analyzing...' : 'Uploading...');
    const form = new FormData();
    form.append('file', file);
    try {
      const params = { force_description_choice: forceSelection, ...overrideParams };
      if (analyzeOnly) params.dry_run = true;
      const r = await axios.post(`${API}/upload`, form, { params });
      setLastRaw(r.data);
      if (r.data.status === 'needs_confirmation') {
        setNeedsConfirm(true);
        setCandidates(r.data.candidates || []);
        setSuggested(r.data.suggested || null);
        setStatus(r.data.message || 'Confirmation needed');
      } else if (r.data.status === 'ok') {
        const mode = analyzeOnly? 'Analyzed' : 'Uploaded';
        const descCol = r.data.description_column_used || 'N/A';
        const auto = r.data.auto_confirmed ? 'auto-confirmed' : 'explicit/exists';
        setStatus(`${mode} ${r.data.records} records (description=${descCol}, ${auto})`);
        setNeedsConfirm(false);
        setCandidates([]);
        setSuggested(null);
      } else {
        setStatus('Unexpected response');
      }
    } catch (e) {
      setStatus('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const confirm = () => {
    if (!chosen && suggested) setChosen(suggested.column);
    submit({ chosen_description: chosen || (suggested && suggested.column), auto_confirm_description: autoConfirm }, { analyzeOnly:false });
  };

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="space-y-2">
        <input type="file" accept=".csv" onChange={e => { setFile(e.target.files[0]); setStatus(''); setNeedsConfirm(false); }} />
        <div className="flex flex-wrap items-center gap-3">
          <button disabled={!file || uploading} className={`px-4 py-2 rounded text-white ${uploading? 'bg-indigo-400 cursor-wait':'bg-indigo-600 hover:bg-indigo-700'}`} onClick={()=>submit({ auto_confirm_description: autoConfirm }, { analyzeOnly:false })}>{uploading? 'Working...':'Upload'}</button>
          <button disabled={!file || uploading} className={`px-4 py-2 rounded border text-xs ${uploading? 'opacity-50 cursor-wait':'hover:bg-gray-50'}`} onClick={()=>submit({ auto_confirm_description: false }, { analyzeOnly:true })}>Analyze (dry-run)</button>
          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input type="checkbox" checked={autoConfirm} onChange={e=>setAutoConfirm(e.target.checked)} /> Auto-confirm high confidence
          </label>
          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input type="checkbox" checked={forceSelection} onChange={e=>setForceSelection(e.target.checked)} /> Force column selection
          </label>
          <button type="button" className="text-xs underline text-gray-500" onClick={()=>setShowDebug(s=>!s)}>{showDebug? 'Hide Raw':'Show Raw'}</button>
        </div>
      </div>
      {status && <div className="text-sm">{status}</div>}
      {showDebug && lastRaw && (
        <pre className="text-[10px] bg-gray-900 text-gray-100 p-2 rounded max-h-64 overflow-auto">{JSON.stringify(lastRaw, null, 2)}</pre>
      )}
      {needsConfirm && (
        <div className="border rounded p-4 bg-white space-y-3">
          <h4 className="font-semibold text-sm">Select Description Column</h4>
          <p className="text-xs text-gray-600">We detected candidate columns that could serve as the narrative description. Pick one below or toggle auto-confirm for future uploads.</p>
          <div className="max-h-56 overflow-auto border rounded">
            <table className="min-w-full text-xs">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="px-2 py-1 text-left">Column</th>
                  <th className="px-2 py-1">Score</th>
                  <th className="px-2 py-1">Non-Empty</th>
                  <th className="px-2 py-1">Richness</th>
                  <th className="px-2 py-1">Examples</th>
                  <th className="px-2 py-1">Choose</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map(c => (
                  <tr key={c.column} className={`odd:bg-white even:bg-gray-50 ${suggested && suggested.column === c.column ? 'ring-1 ring-indigo-300' : ''}`}>
                    <td className="px-2 py-1 font-mono break-all">{c.column}</td>
                    <td className="px-2 py-1 text-center">{c.score}</td>
                    <td className="px-2 py-1 text-center">{c.non_empty_ratio}</td>
                    <td className="px-2 py-1 text-center">{c.richness}</td>
                    <td className="px-2 py-1 max-w-xs">
                      <div className="flex flex-col gap-1">
                        {(c.examples||[]).map((ex,i)=>(<span key={i} className="truncate" title={ex}>{ex}</span>))}
                      </div>
                    </td>
                    <td className="px-2 py-1 text-center">
                      <input type="radio" name="chosenDesc" value={c.column} checked={chosen === c.column} onChange={()=>setChosen(c.column)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={confirm} disabled={uploading} className="px-3 py-2 rounded bg-indigo-600 text-white text-xs hover:bg-indigo-700">Confirm Selection</button>
            <button onClick={()=>{ setNeedsConfirm(false); setCandidates([]); setSuggested(null); setChosen(''); setStatus('Cancelled'); }} className="px-3 py-2 rounded border text-xs">Cancel</button>
          </div>
          {suggested && !chosen && <div className="text-[11px] text-gray-500">Suggested: <strong>{suggested.column}</strong> (score {suggested.score}). Select it or confirm directly.</div>}
        </div>
      )}
    </div>
  );
}
