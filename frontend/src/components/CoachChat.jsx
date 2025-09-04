import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function CoachChat({ API }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [fast, setFast] = useState(false);
  const [recs, setRecs] = useState(null);
  const [loadedHistory, setLoadedHistory] = useState(false);

  useEffect(() => {
    // Load prior conversation history on first mount
    const load = async () => {
      try {
        const r = await axios.get(`${API}/coach/history?limit=25`);
        if (Array.isArray(r.data)) {
          const histMsgs = r.data.map(m => ({ role: m.role, content: m.content, formatted: true, id: m.id }));
          setMessages(histMsgs);
        }
      } catch (e) { /* ignore (likely unauthenticated) */ }
      finally { setLoadedHistory(true); }
    };
    load();
  }, [API]);
  const [loadingRecs, setLoadingRecs] = useState(false);

  function formatAssistant(content) {
    // Very lightweight markdown-ish formatter: headings, bullet lists, emphasis
    const lines = content.split(/\r?\n/);
    const elements = [];
    let listBuffer = [];
    const flushList = () => {
      if (listBuffer.length) {
        elements.push(<ul key={elements.length} className="list-disc pl-5 space-y-1">{listBuffer.map((li,i)=><li key={i}>{li}</li>)}</ul>);
        listBuffer = [];
      }
    };
    for (let raw of lines) {
      const line = raw.trim();
      if (!line) { flushList(); continue; }
      // Heading (simple heuristic)
      if (/^(#+\s|\*\*?\s?)[A-Za-z]/.test(line) || /^[A-Z][A-Z \-]{3,}$/.test(line)) {
        flushList();
        const clean = line.replace(/^#+\s*/, '').replace(/^\*+\s*/, '').trim();
        elements.push(<h4 key={elements.length} className="font-semibold mt-3 text-indigo-700">{clean}</h4>);
        continue;
      }
      // Bullet
      if (/^[-*•]\s+/.test(line)) {
        listBuffer.push(line.replace(/^[-*•]\s+/, ''));
        continue;
      }
      // Numbered list
      if (/^\d+\.\s+/.test(line)) {
        listBuffer.push(line.replace(/^\d+\.\s+/, ''));
        continue;
      }
      // Paragraph
      flushList();
      // Bold patterns **text**
      const parts = [];
      let idx = 0; let bold = false;
      const segments = line.split(/(\*\*[^*]+\*\*)/g);
      for (const seg of segments) {
        if (/^\*\*[^*]+\*\*$/.test(seg)) {
            parts.push(<strong key={idx++}>{seg.slice(2,-2)}</strong>);
        } else if (seg) {
            parts.push(<span key={idx++}>{seg}</span>);
        }
      }
      elements.push(<p key={elements.length} className="leading-snug mt-2">{parts}</p>);
    }
    flushList();
    return <div className="text-sm whitespace-pre-wrap">{elements}</div>;
  }

  const send = async () => {
    if(!input) return;
    const newMessages = [...messages, { role: 'user', content: input }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);
    try {
  const r = await axios.post(`${API}/coach?include_history=true`, { message: input, fast });
      setMessages([...newMessages, { role: 'assistant', content: r.data.response, formatted: true }]);
    } catch(e) {
      const msg = e?.response?.status === 401 ? 'Please login to use the coach.' : 'Error fetching advice.';
      setMessages([...newMessages, { role: 'assistant', content: msg }]);
    } finally {
      setLoading(false);
    }
  };

  const loadRecommendations = async () => {
    setLoadingRecs(true);
    try {
      const r = await axios.get(`${API}/coach/recommendations`);
      setRecs(r.data);
      setMessages(m=>[...m, { role:'assistant', content: r.data.recommendations, formatted: true }]);
    } catch(e) {
      setMessages(m=>[...m, { role:'assistant', content: 'Error fetching recommendations.' }]);
    } finally {
      setLoadingRecs(false);
    }
  };

  const sendFeedback = async (msg, helpful) => {
    if (!msg.id) return;
  try { await axios.post(`${API}/coach/feedback`, null, { params: { message_id: msg.id, helpful } }); } catch(e) {}
  };

  const clearHistory = async () => {
  try { await axios.delete(`${API}/coach/history`); setMessages([]);} catch(e) {}
  };

  return (
    <div className="max-w-2xl space-y-4">
      <div className="border rounded p-4 h-80 overflow-y-auto bg-white space-y-2">
        {messages.map((m,i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            {m.role === 'user' ? (
              <span className='inline-block bg-indigo-600 text-white px-3 py-2 rounded mb-1 max-w-full break-words text-sm'>{m.content}</span>
            ) : (
              <div className='inline-block bg-gray-100 px-3 py-2 rounded mb-1 max-w-full text-left shadow-sm border border-gray-200'>
                {m.formatted ? formatAssistant(m.content) : m.content}
                {m.role === 'assistant' && (
                  <div className='flex gap-1 mt-1 text-[10px] text-gray-500'>
                    <button onClick={()=>sendFeedback(m,true)} className='hover:text-green-600'>👍</button>
                    <button onClick={()=>sendFeedback(m,false)} className='hover:text-red-600'>👎</button>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-sm text-gray-500">Thinking...</div>}
      </div>
      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} className="flex-1 border rounded px-3 py-2" placeholder="Ask for advice..." />
          <button onClick={send} disabled={loading} className="bg-indigo-600 disabled:bg-indigo-400 text-white px-4 py-2 rounded">Send</button>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-600">
          <label className="flex items-center gap-1 cursor-pointer select-none">
            <input type="checkbox" checked={fast} onChange={e=>setFast(e.target.checked)} /> Fast
          </label>
          <span className="text-[10px] uppercase tracking-wide">Fast mode trims context & tokens for quicker replies</span>
          <button onClick={loadRecommendations} disabled={loadingRecs} className="ml-auto bg-emerald-600 disabled:bg-emerald-400 text-white px-3 py-1 rounded text-xs">{loadingRecs? 'Loading...' : 'Safe Save Ideas'}</button>
        </div>
  {recs && (
          <div className="border rounded p-3 bg-white text-xs space-y-2">
            <div className="font-semibold text-gray-700">Instrument Bands</div>
            <div className="grid md:grid-cols-2 gap-3">
              {Object.entries(recs.bands || {}).map(([band,list])=> (
                <div key={band} className="border rounded p-2">
                  <div className="text-indigo-600 font-medium mb-1">{band}</div>
                  <ul className="space-y-1">
                    {list.map((i,idx)=>(
                      <li key={idx} className="flex justify-between gap-2">
                        <span className="truncate" title={i.name}>{i.ticker || i.name}</span>
                        <span className="text-gray-500">{i.yield_pct ? `${i.yield_pct}%` : ''}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <div className="text-[10px] text-gray-500">{recs.disclaimer}</div>
          </div>
  )}
  <button onClick={clearHistory} className='self-start text-[10px] underline text-gray-500'>Clear History</button>
      </div>
    </div>
  );
}
