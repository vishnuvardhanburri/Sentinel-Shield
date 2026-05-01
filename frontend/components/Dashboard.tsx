'use client';
/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, react-hooks/set-state-in-effect, react-hooks/immutability, react-hooks/exhaustive-deps */

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck, ShieldAlert, Upload, Search, Lock, Activity,
  FileText, AlertTriangle, Send, Loader2, Users, Settings,
  BarChart3, ClipboardList, BookOpen, LogOut, RefreshCw,
  CheckCircle2, XCircle, Eye, Download, ChevronRight,
  Zap, Globe, Server, Database, Key, Bell, ToggleLeft, ToggleRight
} from 'lucide-react';
import axios from 'axios';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Helpers ──────────────────────────────────────────────────────────────────
const api = axios.create({ baseURL: API_BASE });
api.interceptors.request.use(cfg => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('sentinel_token') : null;
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

const grade_color: Record<string, string> = {
  A: 'text-emerald-400', B: 'text-blue-400', C: 'text-yellow-400',
  D: 'text-orange-400', F: 'text-rose-400'
};

const risk_color = (score: number) =>
  score >= 7 ? 'text-rose-400' : score >= 4 ? 'text-amber-400' : 'text-emerald-400';

// ── Login Screen ─────────────────────────────────────────────────────────────
function LoginScreen({ onLogin }: { onLogin: (token: string, role: string, forcePasswordChange: boolean, user: any) => void }) {
  const [email, setEmail] = useState('admin@sentinel.local');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    setLoading(true); setError('');
    try {
      const res = await axios.post(`${API_BASE}/api/v2/auth/login`, { email, password });
      localStorage.setItem('sentinel_token', res.data.access_token);
      localStorage.setItem('sentinel_user', JSON.stringify(res.data.user || {}));
      onLogin(res.data.access_token, res.data.user?.role || 'STAFF', !!res.data.force_password_change, res.data.user || {});
    } catch {
      setError('Invalid credentials. Use the first-run bootstrap password printed in backend logs.');
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#030303] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-emerald-950/40 via-transparent to-transparent" />
      <motion.div
        initial={{ opacity: 0, y: 32 }} animate={{ opacity: 1, y: 0 }}
        className="relative w-full max-w-md"
      >
        <div className="mb-8 text-center">
          <div className="w-16 h-16 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-[0_0_40px_rgba(16,185,129,0.15)] overflow-hidden">
            <span className="text-2xl font-black text-emerald-300 tracking-tight">XT</span>
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">SENTINEL <span className="text-emerald-400">SHIELD</span></h1>
          <p className="text-emerald-500/80 text-xs uppercase tracking-[0.2em] font-bold mt-2 font-display">BY XAVIRA TECH LABS</p>
        </div>

        <div className="bg-white/[0.03] border border-white/10 rounded-3xl p-8 backdrop-blur-sm">
          {error && (
            <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm flex items-center gap-2">
              <XCircle size={14} /> {error}
            </div>
          )}
          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-2">Email</label>
              <input id="login-email" value={email} onChange={e => setEmail(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500/50 transition-all"
                placeholder="you@org.com" />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-2">Password</label>
              <input id="login-password" type="password" value={password} onChange={e => setPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleLogin()}
                className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500/50 transition-all"
                placeholder="••••••••" />
            </div>
            <button id="login-btn" onClick={handleLogin} disabled={loading}
              className="w-full bg-emerald-500 hover:bg-emerald-400 text-black font-bold py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 mt-2 shadow-[0_0_24px_rgba(16,185,129,0.25)]">
              {loading ? <Loader2 size={18} className="animate-spin" /> : <ShieldCheck size={18} />}
              {loading ? 'Authenticating…' : 'Secure Login'}
            </button>
          </div>
          <div className="mt-5 pt-5 border-t border-white/5">
            <p className="text-xs text-slate-600 text-center">First-run credentials are generated once in backend logs.</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

function PasswordChangeScreen({ onChanged }: { onChanged: () => void }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    setError('');
    if (newPassword.length < 14) {
      setError('New password must be at least 14 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await api.post('/api/v2/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      localStorage.removeItem('sentinel_token');
      localStorage.removeItem('sentinel_user');
      onChanged();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Password change failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030303] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white/[0.03] border border-white/10 rounded-3xl p-8">
        <div className="mb-7 text-center">
          <div className="w-14 h-14 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Key className="text-amber-400" size={24} />
          </div>
          <h1 className="text-2xl font-black text-white">Rotate Temporary Password</h1>
          <p className="text-xs text-slate-500 mt-2">Required before protected Sentinel Shield features unlock.</p>
        </div>
        {error && <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm">{error}</div>}
        <div className="space-y-4">
          <input id="current-password" type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)}
            placeholder="Temporary password"
            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500/50" />
          <input id="new-password" type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)}
            placeholder="New password, 14+ characters"
            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500/50" />
          <input id="confirm-password" type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            placeholder="Confirm new password"
            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500/50" />
          <button id="change-password-btn" onClick={submit} disabled={loading}
            className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-black font-bold py-3.5 rounded-xl flex items-center justify-center gap-2">
            {loading ? <Loader2 className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
            Change Password
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, glow = 'emerald', icon: Icon }:
  { label: string; value: string | number; sub: string; glow?: string; icon: any }) {
  const glows: Record<string, string> = {
    emerald: 'bg-emerald-500/10', rose: 'bg-rose-500/10',
    purple: 'bg-purple-500/10', blue: 'bg-blue-500/10', amber: 'bg-amber-500/10'
  };
  const texts: Record<string, string> = {
    emerald: 'text-emerald-400', rose: 'text-rose-400',
    purple: 'text-purple-400', blue: 'text-blue-400', amber: 'text-amber-400'
  };
  return (
    <div className="p-6 bg-[#0a0a0a] border border-white/8 rounded-2xl relative overflow-hidden group hover:border-white/15 transition-all">
      <div className={`absolute top-0 right-0 w-28 h-28 ${glows[glow]} blur-[60px] group-hover:opacity-150 transition-all`} />
      <div className={`w-9 h-9 ${glows[glow]} rounded-xl flex items-center justify-center mb-4`}>
        <Icon size={18} className={texts[glow]} />
      </div>
      <p className="text-slate-500 text-xs font-bold uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-4xl font-black mb-1 ${texts[glow]}`}>{value}</p>
      <p className="text-xs text-slate-600">{sub}</p>
    </div>
  );
}

// ── Overview Tab ──────────────────────────────────────────────────────────────
function OverviewTab({ status }: { status: any }) {
  const stats = status?.stats || {};
  const audit = status?.audit || {};
  const infra = status?.infra || {};
  const policies = status?.policies || {};
  const models = status?.available_models || {};

  const riskHistory = [
    { t: '06:00', risk: 1.2 }, { t: '08:00', risk: 2.8 }, { t: '10:00', risk: 4.1 },
    { t: '12:00', risk: 3.3 }, { t: '14:00', risk: 5.9 }, { t: '16:00', risk: 4.2 },
    { t: '18:00', risk: 2.1 }, { t: '20:00', risk: 1.8 },
  ];

  const frameworkScores = status?.compliance_score?.framework_scores
    ? Object.entries(status.compliance_score.framework_scores).map(([k, v]) => ({ name: k.replace('_LITE', ''), val: v as number }))
    : [{ name: 'HIPAA', val: 95 }, { name: 'DPDP', val: 87 }, { name: 'GDPR', val: 91 }];

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard icon={ShieldCheck} label="Leaks Blocked" value={stats.leaks_blocked ?? 0} sub="Total interceptions" glow="emerald" />
        <StatCard icon={FileText} label="Audit Events" value={audit.total_events ?? 0} sub="Immutable log entries" glow="blue" />
        <StatCard icon={AlertTriangle} label="High-Risk Events" value={audit.high_risk_blocked ?? 0} sub="Risk score > 7.0" glow="rose" />
        <StatCard icon={Zap} label="Redactions Applied" value={audit.total_redactions ?? 0} sub="PII tokens removed" glow="amber" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 p-6 bg-[#0a0a0a] border border-white/8 rounded-2xl">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-5">Risk Score Timeline</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={riskHistory}>
                <defs>
                  <linearGradient id="rg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" vertical={false} />
                <XAxis dataKey="t" stroke="#333" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis domain={[0, 10]} stroke="#333" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: '#111', border: '1px solid #222', borderRadius: 12, fontSize: 12 }} itemStyle={{ color: '#10b981' }} />
                <Area type="monotone" dataKey="risk" stroke="#10b981" fill="url(#rg)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="p-6 bg-[#0a0a0a] border border-white/8 rounded-2xl">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-5">Compliance Scores</h3>
          <div className="space-y-3">
            {frameworkScores.map(f => (
              <div key={f.name}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">{f.name}</span>
                  <span className={f.val >= 90 ? 'text-emerald-400' : f.val >= 75 ? 'text-blue-400' : 'text-amber-400'}>{f.val}</span>
                </div>
                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${f.val >= 90 ? 'bg-emerald-500' : f.val >= 75 ? 'bg-blue-500' : 'bg-amber-500'}`}
                    style={{ width: `${f.val}%` }} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-5 pt-4 border-t border-white/5">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${audit.chain_integrity ? 'bg-emerald-500' : 'bg-rose-500'}`} />
              <span className="text-xs text-slate-500">Audit chain {audit.chain_integrity ? 'VERIFIED ✓' : '⚠ BROKEN'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Infra + Policies */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-5 bg-[#0a0a0a] border border-white/8 rounded-2xl space-y-3">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">System Health</h3>
          {[
            { label: 'Deployment Mode', val: infra.deployment_mode || 'AIRGAP', icon: Server },
            { label: 'Disk Free', val: `${infra.disk_free_gb ?? '??'} GB`, icon: Database },
            { label: 'AI Engine', val: infra.ai_pulse || 'UNKNOWN', icon: Zap },
            { label: 'Hardware ID', val: infra.hardware_id || '…', icon: Key },
          ].map(row => (
            <div key={row.label} className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-500">
                <row.icon size={13} />
                <span className="text-xs">{row.label}</span>
              </div>
              <span className="text-xs font-mono text-slate-300">{row.val}</span>
            </div>
          ))}
        </div>

        <div className="p-5 bg-[#0a0a0a] border border-white/8 rounded-2xl space-y-3">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Policy Engine</h3>
          <div className="text-3xl font-black text-white">{policies.total_rules ?? 0} <span className="text-sm font-normal text-slate-500">rules loaded</span></div>
          <div className="space-y-1.5">
            {Object.entries(policies.department_policies || {}).slice(0, 4).map(([dept, count]) => (
              <div key={dept} className="flex justify-between text-xs">
                <span className="text-slate-500">{dept}</span>
                <span className="text-emerald-400">{count as number} rules</span>
              </div>
            ))}
          </div>
        </div>

        <div className="p-5 bg-[#0a0a0a] border border-white/8 rounded-2xl space-y-3">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Model Gateway</h3>
          {Object.keys(models).length === 0
            ? <p className="text-xs text-slate-600">No models connected</p>
            : Object.entries(models).map(([m, ok]) => (
              <div key={m} className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-mono">{m}</span>
                <div className={`w-2 h-2 rounded-full ${ok ? 'bg-emerald-500' : 'bg-rose-500'}`} />
              </div>
            ))
          }
        </div>
      </div>
    </motion.div>
  );
}

// ── Vault Intelligence Tab ─────────────────────────────────────────────────────
function VaultTab({ role }: { role: string }) {
  const [query, setQuery] = useState('');
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [dept, setDept] = useState('');
  const [model, setModel] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [history]);

  const ask = async () => {
    if (!query.trim()) return;
    const q = query; setQuery(''); setLoading(true);
    setHistory(h => [...h, { role: 'user', content: q }]);
    try {
      const res = await api.post('/ask', { prompt: q, department: dept || undefined, preferred_model: model || undefined });
      setHistory(h => [...h, { role: 'bot', ...res.data }]);
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      const blocked = typeof detail === 'object' && detail?.action === 'BLOCKED';
      setHistory(h => [...h, {
        role: 'bot',
        answer: blocked ? `🚨 BLOCKED by policy: ${detail.reason}` : `Error: ${e.response?.status || 'No response from backend'}`,
        findings_alert: blocked ? 'BLOCKED' : 'ERROR',
        risk_score: 10,
      }]);
    } finally { setLoading(false); }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col h-[76vh] bg-[#080808] border border-white/8 rounded-2xl overflow-hidden">
      <div className="p-5 border-b border-white/8 flex items-center justify-between bg-[#060606]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-emerald-500/15 rounded-lg flex items-center justify-center">
            <ShieldCheck className="text-emerald-400" size={16} />
          </div>
          <div>
            <p className="font-bold text-white text-sm">Vault AI</p>
            <p className="text-xs text-slate-600">Private local assistant · scanned · masked · audit logged</p>
          </div>
        </div>
        <div className="flex gap-2">
          <select id="dept-select" value={dept} onChange={e => setDept(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-400 focus:outline-none">
            <option value="">All Departments</option>
            {['HOSPITAL', 'ICU', 'LEGAL', 'FINANCE', 'HR', 'LAW_FIRM', 'IVF_CLINIC'].map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <select id="model-select" value={model} onChange={e => setModel(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-400 focus:outline-none">
            <option value="">Vault AI Local</option>
            <option value="ollama/llama3.1">Llama 3.1 Local</option>
            <option value="ollama/llama3.2">Llama 3.2 Local</option>
            <option value="ollama/deepseek-r1:8b">DeepSeek R1 Local</option>
          </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {history.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center mb-4 border border-white/8">
              <Lock className="text-slate-500" size={24} />
            </div>
            <p className="font-bold text-white mb-1">Private Local AI Interface</p>
            <p className="text-sm text-slate-600 max-w-xs">Ask anything. Vault AI answers through your own local model, with sensitive data masked before inference.</p>
          </div>
        )}
        {history.map((msg, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[78%] p-4 rounded-2xl text-sm leading-relaxed ${msg.role === 'user'
              ? 'bg-emerald-600/90 text-white'
              : msg.findings_alert === 'BLOCKED' ? 'bg-rose-950/50 border border-rose-500/20 text-rose-300'
                : 'bg-white/[0.04] border border-white/8 text-slate-200'}`}>
              {msg.role === 'bot' && (
                <div className="flex flex-wrap gap-2 mb-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${msg.findings_alert === 'CLEAN' ? 'bg-emerald-500/15 text-emerald-400'
                    : msg.findings_alert === 'BLOCKED' ? 'bg-rose-500/20 text-rose-400'
                      : 'bg-amber-500/15 text-amber-400'}`}>
                    {msg.findings_alert || 'CLEAN'}
                  </span>
                  {msg.risk_score != null && (
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold bg-white/5 ${risk_color(msg.risk_score)}`}>
                      Risk {msg.risk_score?.toFixed(1)}
                    </span>
                  )}
                  {msg.redactions_applied > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-purple-500/15 text-purple-400">
                      {msg.redactions_applied} redacted
                    </span>
                  )}
                  {msg.model_used && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-blue-500/10 text-blue-400">
                      {msg.model_used}
                    </span>
                  )}
                </div>
              )}
              <p className="whitespace-pre-wrap">{msg.answer || msg.content}</p>
            </div>
          </motion.div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white/5 border border-white/8 p-4 rounded-2xl flex items-center gap-3">
              <Loader2 className="animate-spin text-emerald-500" size={16} />
              <span className="text-sm text-slate-500">Scanning · Redacting · Routing…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-5 border-t border-white/8 bg-[#060606]">
        <div className="flex gap-3">
          <input id="vault-query-input" value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && ask()}
            placeholder="Ask your secure vault anything…"
            className="flex-1 bg-white/5 border border-white/10 rounded-xl py-3 px-5 text-sm text-white focus:outline-none focus:border-emerald-500/40 transition-all placeholder:text-slate-600" />
          <button id="vault-send-btn" onClick={ask} disabled={loading || !query.trim()}
            className="w-11 h-11 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 rounded-xl flex items-center justify-center text-black transition-all shadow-[0_0_16px_rgba(16,185,129,0.2)]">
            <Send size={16} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

// ── Audit Log Tab ─────────────────────────────────────────────────────────────
function AuditLogTab() {
  const [entries, setEntries] = useState<any[]>([]);
  const [chainValid, setChainValid] = useState(true);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => { loadAudit(); }, []);

  const loadAudit = async () => {
    setLoading(true);
    try {
      const res = await api.get('/audit/log?limit=100');
      setEntries(res.data.entries || []);
      setChainValid(res.data.chain_valid !== false);
    } catch { } finally { setLoading(false); }
  };

  const exportAudit = async (fmt: string) => {
    setExporting(true);
    try {
      const res = await api.post(`/export-audit?format=${fmt}`);
      alert(`✅ Exported: ${res.data.file}`);
    } catch { alert('Export failed — check backend.'); } finally { setExporting(false); }
  };

  const generateEvidenceReport = async () => {
    setExporting(true);
    try {
      const res = await api.post('/api/v2/audit/report', { org_name: 'Buyer Organization', limit: 500 });
      alert(`Evidence report generated: ${res.data.file}\nCertificate: ${res.data.certificate}`);
    } catch { alert('Evidence report failed — check backend and ReportLab.'); } finally { setExporting(false); }
  };

  const actionColor = (a: string) => {
    if (a?.includes('BLOCK')) return 'bg-rose-500/15 text-rose-400';
    if (a?.includes('QUERY')) return 'bg-blue-500/15 text-blue-400';
    if (a?.includes('STARTUP')) return 'bg-slate-500/15 text-slate-400';
    return 'bg-emerald-500/15 text-emerald-400';
  };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-white">Immutable Audit Ledger</h2>
          <span className={`text-xs px-2 py-1 rounded-full font-bold ${chainValid ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'}`}>
            {chainValid ? '⛓ Chain Verified' : '⚠ Chain Broken'}
          </span>
        </div>
        <div className="flex gap-2">
          <button id="audit-refresh-btn" onClick={loadAudit} className="p-2 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all">
            <RefreshCw size={14} className="text-slate-400" />
          </button>
          <button id="audit-export-csv-btn" onClick={() => exportAudit('csv')} disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-xs font-bold text-slate-300 hover:bg-white/10 transition-all">
            <Download size={13} /> CSV
          </button>
          <button id="audit-export-pdf-btn" onClick={() => exportAudit('pdf')} disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs font-bold text-emerald-400 hover:bg-emerald-500/20 transition-all">
            <FileText size={13} /> PDF Report
          </button>
          <button id="audit-evidence-report-btn" onClick={generateEvidenceReport} disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs font-bold text-blue-400 hover:bg-blue-500/20 transition-all">
            <ShieldCheck size={13} /> Evidence
          </button>
        </div>
      </div>

      <div className="bg-[#080808] border border-white/8 rounded-2xl overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/8">
              {['Timestamp', 'User', 'Role', 'Action', 'Dept', 'Risk', 'Redactions', 'Policy'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-slate-600 font-bold uppercase tracking-widest text-[10px]">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-600">
                <Loader2 size={18} className="animate-spin mx-auto" />
              </td></tr>
            ) : entries.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-600">No audit entries yet. Run a query to generate logs.</td></tr>
            ) : entries.map((e, i) => (
              <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-all">
                <td className="px-4 py-2.5 font-mono text-slate-500">{e.timestamp?.slice(0, 16).replace('T', ' ')}</td>
                <td className="px-4 py-2.5 text-slate-300 truncate max-w-[120px]">{e.user_id}</td>
                <td className="px-4 py-2.5 text-slate-500">{e.user_role}</td>
                <td className="px-4 py-2.5">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${actionColor(e.action)}`}>{e.action}</span>
                </td>
                <td className="px-4 py-2.5 text-slate-500">{e.department || '—'}</td>
                <td className="px-4 py-2.5">
                  <span className={risk_color(e.risk_score ?? 0)}>{e.risk_score?.toFixed(1) ?? '—'}</span>
                </td>
                <td className="px-4 py-2.5 text-slate-500">{e.redactions_applied?.length || 0}</td>
                <td className="px-4 py-2.5 text-slate-600 truncate max-w-[100px]">{e.policy_triggered || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-700 text-right font-mono">SHA-256 hash chain · every entry cryptographically linked</p>
    </motion.div>
  );
}

// ── Policy Editor Tab ─────────────────────────────────────────────────────────
function PolicyTab({ role }: { role: string }) {
  const [summary, setSummary] = useState<any>({});
  const [yaml, setYaml] = useState(`department: MY_DEPARTMENT
policy_name: My Custom Policy

rules:
  - name: Block Patient Names
    description: Block raw patient identifiers from AI models
    entity_types:
      - PERSON
    keywords:
      - "patient name"
      - "uhid"
    enforcement: block
    risk_threshold: 6.0
`);
  const [validation, setValidation] = useState<any>(null);
  const [reloading, setReloading] = useState(false);
  const canEdit = ['SUPER_ADMIN', 'DEPARTMENT_HEAD'].includes(role);

  useEffect(() => {
    api.get('/policy/list').then(r => setSummary(r.data)).catch(() => { });
  }, []);

  const validateYaml = async () => {
    try {
      const res = await api.post('/policy/validate-yaml', { yaml_content: yaml });
      setValidation(res.data);
    } catch {
      setValidation({ valid: false, errors: ['Backend validation unavailable — check YAML syntax manually.'], rules_parsed: 0 });
    }
  };

  const reloadPolicies = async () => {
    setReloading(true);
    try {
      const res = await api.post('/policy/reload');
      setSummary(res.data.summary);
      alert('✅ Policies reloaded from disk.');
    } catch { alert('Reload failed.'); } finally { setReloading(false); }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Policy Engine</h2>
          <p className="text-xs text-slate-500">{summary.total_rules ?? 0} rules active across {Object.keys(summary.department_policies || {}).length} departments</p>
        </div>
        {canEdit && (
          <button id="policy-reload-btn" onClick={reloadPolicies} disabled={reloading}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs font-bold text-emerald-400 hover:bg-emerald-500/20 transition-all">
            <RefreshCw size={13} className={reloading ? 'animate-spin' : ''} /> Reload from Disk
          </button>
        )}
      </div>

      <div className="grid grid-cols-5 gap-4">
        {/* Dept list */}
        <div className="col-span-2 p-5 bg-[#080808] border border-white/8 rounded-2xl space-y-2">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">Loaded Policies</h3>
          <div className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
            <span className="text-xs text-slate-400">Global Rules</span>
            <span className="text-xs font-bold text-emerald-400">{summary.global_rules ?? 0}</span>
          </div>
          {Object.entries(summary.department_policies || {}).map(([dept, count]) => (
            <div key={dept} className="flex items-center justify-between p-3 bg-white/5 rounded-xl hover:bg-white/8 transition-all cursor-pointer">
              <span className="text-xs text-slate-400">{dept}</span>
              <span className="text-xs font-bold text-blue-400">{count as number} rules</span>
            </div>
          ))}
          <div className="mt-4 pt-4 border-t border-white/5">
            <p className="text-[10px] text-slate-700">Presets: hospital · ivf_clinic · law_firm · real_estate · logistics</p>
          </div>
        </div>

        {/* YAML editor */}
        <div className="col-span-3 space-y-3">
          <div className="bg-[#080808] border border-white/8 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-white/8 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">YAML Policy Editor</span>
              {!canEdit && <span className="text-xs text-amber-400 bg-amber-500/10 px-2 py-1 rounded">Read-only</span>}
            </div>
            <textarea id="policy-yaml-editor"
              value={yaml} onChange={e => setYaml(e.target.value)} readOnly={!canEdit}
              className="w-full h-64 bg-transparent font-mono text-xs text-slate-300 p-4 focus:outline-none resize-none placeholder:text-slate-700"
              spellCheck={false} />
          </div>

          {validation && (
            <div className={`p-3 rounded-xl border text-xs ${validation.valid ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}`}>
              {validation.valid
                ? `✅ Valid — ${validation.rules_parsed} rules parsed for "${validation.department}"`
                : `❌ Invalid: ${validation.errors?.join(', ')}`}
            </div>
          )}

          {canEdit && (
            <div className="flex gap-2">
              <button id="policy-validate-btn" onClick={validateYaml}
                className="flex-1 py-2.5 bg-white/5 border border-white/10 rounded-xl text-xs font-bold text-slate-300 hover:bg-white/10 transition-all">
                Validate YAML
              </button>
              <button id="policy-save-btn" onClick={() => alert('Save to presets/ directory and click Reload from Disk.')}
                className="flex-1 py-2.5 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs font-bold text-blue-400 hover:bg-blue-500/20 transition-all">
                Save Policy
              </button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ── User Management Tab ───────────────────────────────────────────────────────
function UsersTab({ role }: { role: string }) {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [tempPassword, setTempPassword] = useState('');
  const [form, setForm] = useState({ email: '', full_name: '', role: 'STAFF', department: 'GENERAL' });

  const roleColors: Record<string, string> = {
    SUPER_ADMIN: 'bg-rose-500/15 text-rose-400',
    DEPARTMENT_HEAD: 'bg-purple-500/15 text-purple-400',
    STAFF: 'bg-blue-500/15 text-blue-400',
    AUDITOR: 'bg-amber-500/15 text-amber-400',
  };
  const canManage = role === 'SUPER_ADMIN';

  const loadUsers = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/v2/admin/users');
      setUsers(res.data.users || []);
    } catch {
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadUsers(); }, []);

  const createUser = async () => {
    if (!form.email.trim()) return;
    setCreating(true); setTempPassword('');
    try {
      const res = await api.post('/api/v2/admin/users', form);
      setTempPassword(`${res.data.user.email}: ${res.data.temporary_password}`);
      setForm({ email: '', full_name: '', role: 'STAFF', department: 'GENERAL' });
      await loadUsers();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'User creation failed.');
    } finally {
      setCreating(false);
    }
  };

  const toggleActive = async (u: any) => {
    try {
      await api.patch(`/api/v2/admin/users/${u.id}`, { is_active: !u.is_active });
      await loadUsers();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'User update failed.');
    }
  };

  const resetPassword = async (u: any) => {
    try {
      const res = await api.post(`/api/v2/admin/users/${u.id}/reset-password`);
      setTempPassword(`${res.data.email}: ${res.data.temporary_password}`);
      await loadUsers();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Password reset failed.');
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">User Management</h2>
          <p className="text-xs text-slate-500">Live RBAC controls · create, disable, reset and force rotation</p>
        </div>
        <button id="users-refresh-btn" onClick={loadUsers}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-xs font-bold text-slate-300 hover:bg-white/10 transition-all">
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {canManage && (
        <div className="p-4 bg-[#080808] border border-white/8 rounded-2xl">
          <div className="grid grid-cols-5 gap-3">
            <input id="new-user-email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
              placeholder="email@company.com" className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none" />
            <input id="new-user-name" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })}
              placeholder="Full name" className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none" />
            <select id="new-user-role" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none">
              {['STAFF', 'DEPARTMENT_HEAD', 'AUDITOR', 'SUPER_ADMIN'].map(r => <option key={r} value={r}>{r}</option>)}
            </select>
            <input id="new-user-dept" value={form.department} onChange={e => setForm({ ...form, department: e.target.value })}
              placeholder="Department" className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none" />
            <button id="add-user-btn" onClick={createUser} disabled={creating}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-black rounded-xl text-xs font-bold flex items-center justify-center gap-2">
              {creating ? <Loader2 className="animate-spin" size={13} /> : <Users size={13} />} Add User
            </button>
          </div>
          {tempPassword && (
            <div className="mt-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300 font-mono">
              Temporary password: {tempPassword}
            </div>
          )}
        </div>
      )}

      <div className="bg-[#080808] border border-white/8 rounded-2xl overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/8">
              {['User', 'Role', 'Department', 'MFA', 'Status', canManage ? 'Actions' : ''].map(h => h && (
                <th key={h} className="text-left px-5 py-3 text-slate-600 font-bold uppercase tracking-widest text-[10px]">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={canManage ? 6 : 5} className="px-5 py-8 text-center text-slate-600"><Loader2 className="animate-spin mx-auto" size={18} /></td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={canManage ? 6 : 5} className="px-5 py-8 text-center text-slate-600">No users visible for this role.</td></tr>
            ) : users.map((u, i) => (
              <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-all">
                <td className="px-5 py-3.5 text-slate-200">{u.email}</td>
                <td className="px-5 py-3.5">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${roleColors[u.role]}`}>{u.role}</span>
                </td>
                <td className="px-5 py-3.5 text-slate-500">{u.department || 'Cross-dept'}</td>
                <td className="px-5 py-3.5">
                  {u.mfa_enabled
                    ? <CheckCircle2 size={14} className="text-emerald-400" />
                    : <XCircle size={14} className="text-slate-700" />}
                </td>
                <td className="px-5 py-3.5">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${u.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                    {u.is_active ? 'ACTIVE' : 'DISABLED'}
                  </span>
                </td>
                {canManage && (
                  <td className="px-5 py-3.5 flex gap-2">
                    <button onClick={() => resetPassword(u)} className="text-amber-400/70 hover:text-amber-300 transition-all text-[10px] font-bold">RESET</button>
                    <button onClick={() => toggleActive(u)} className="text-slate-500 hover:text-slate-300 transition-all text-[10px] font-bold">
                      {u.is_active ? 'DISABLE' : 'ENABLE'}
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { role: 'SUPER_ADMIN', perms: 'Full access · license management · all departments' },
          { role: 'DEPARTMENT_HEAD', perms: 'Own dept policies · audit export · user view' },
          { role: 'STAFF', perms: 'AI queries · document ingestion · own session view' },
        ].map(r => (
          <div key={r.role} className="p-4 bg-[#080808] border border-white/8 rounded-xl">
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${roleColors[r.role]}`}>{r.role}</span>
            <p className="text-xs text-slate-600 mt-2">{r.perms}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

// ── Compliance Tab ─────────────────────────────────────────────────────────────
function ComplianceTab() {
  const [score, setScore] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/compliance/score').then(r => setScore(r.data)).catch(() => { }).finally(() => setLoading(false));
  }, []);

  const frameworks = score?.framework_scores
    ? Object.entries(score.framework_scores).map(([k, v]) => ({ name: k, val: v as number, grade: score.framework_grades?.[k] }))
    : [];

  const pieData = frameworks.length > 0
    ? frameworks.map(f => ({ name: f.name.replace('_LITE', ''), value: f.val }))
    : [{ name: 'Loading', value: 100 }];

  const PIE_COLORS = ['#10b981', '#3b82f6', '#a855f7', '#f59e0b'];

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <h2 className="text-lg font-bold text-white">Compliance Scorecard</h2>

      {loading ? (
        <div className="flex items-center justify-center h-40"><Loader2 className="animate-spin text-emerald-500" /></div>
      ) : (
        <>
          <div className="grid grid-cols-4 gap-4">
            <div className="col-span-1 p-6 bg-[#080808] border border-white/8 rounded-2xl flex flex-col items-center justify-center">
              <p className={`text-7xl font-black ${grade_color[score?.grade] || 'text-slate-400'}`}>{score?.grade || '—'}</p>
              <p className="text-xs text-slate-500 mt-2">Composite Grade</p>
              <p className="text-2xl font-bold text-white mt-1">{score?.composite_score ?? 0}</p>
              {score?.zero_incident_badge && (
                <span className="mt-3 text-[10px] px-2 py-1 bg-emerald-500/15 text-emerald-400 rounded-full font-bold">🏅 Zero Incidents</span>
              )}
            </div>

            <div className="col-span-2 p-6 bg-[#080808] border border-white/8 rounded-2xl">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Framework Breakdown</h3>
              <div className="space-y-3">
                {frameworks.map(f => (
                  <div key={f.name}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">{f.name.replace('_LITE', '')}</span>
                      <span className={grade_color[f.grade] || 'text-slate-400'}>{f.val} · {f.grade}</span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${f.val >= 90 ? 'bg-emerald-500' : f.val >= 75 ? 'bg-blue-500' : 'bg-amber-500'}`}
                        style={{ width: `${f.val}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-6 bg-[#080808] border border-white/8 rounded-2xl flex flex-col items-center justify-center">
              <div className="h-32 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={35} outerRadius={55} dataKey="value" strokeWidth={0}>
                      {pieData.map((_, idx) => <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />)}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <p className="text-xs text-slate-600 text-center">Multi-framework distribution</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Total Redactions', val: score?.total_redactions ?? 0, color: 'text-purple-400' },
              { label: 'High-Risk Blocked', val: score?.high_risk_blocked ?? 0, color: 'text-rose-400' },
              { label: 'Open Incidents', val: score?.open_incidents ?? 0, color: score?.open_incidents > 0 ? 'text-rose-400' : 'text-emerald-400' },
            ].map(s => (
              <div key={s.label} className="p-5 bg-[#080808] border border-white/8 rounded-2xl">
                <p className="text-xs text-slate-500 uppercase tracking-widest">{s.label}</p>
                <p className={`text-4xl font-black mt-2 ${s.color}`}>{s.val}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </motion.div>
  );
}

// ── Oracle Risk Tab ──────────────────────────────────────────────────────────
function RiskTab() {
  const [heatmap, setHeatmap] = useState<any>(null);
  const [diagnostics, setDiagnostics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [riskRes, diagRes] = await Promise.all([
        api.get('/api/v2/risk/heatmap'),
        api.get('/api/v2/system/diagnostics'),
      ]);
      setHeatmap(riskRes.data);
      setDiagnostics(diagRes.data);
    } catch { } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const actors = heatmap?.actors || [];
  const checks = diagnostics?.checks || [];

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Oracle Risk Heatmap</h2>
          <p className="text-xs text-slate-500">Real-time actor scoring · quarantine · self-diagnostics</p>
        </div>
        <button onClick={load} className="p-2 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all">
          <RefreshCw size={14} className={loading ? 'animate-spin text-emerald-400' : 'text-slate-400'} />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard icon={Users} label="Tracked Actors" value={actors.length} sub="1-hour risk window" glow="blue" />
        <StatCard icon={Lock} label="Quarantined" value={heatmap?.quarantined_users ?? 0} sub="Auto-contained identities" glow="rose" />
        <StatCard icon={ShieldCheck} label="Self Check" value={diagnostics?.ready ? 'READY' : 'HOLD'} sub="Local LLM · ledger · scanner" glow={diagnostics?.ready ? 'emerald' : 'amber'} />
      </div>

      <div className="grid grid-cols-5 gap-4">
        <div className="col-span-3 bg-[#080808] border border-white/8 rounded-2xl overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/8">
                {['Actor Hash', 'Risk', 'PII/hr', 'Injection/hr', 'Semantic/hr', 'State'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-slate-600 font-bold uppercase tracking-widest text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {actors.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-600">No risk events yet.</td></tr>
              ) : actors.map((actor: any) => (
                <tr key={actor.actor_hash} className="border-b border-white/[0.04]">
                  <td className="px-4 py-2.5 font-mono text-slate-400">{actor.actor_hash.slice(0, 22)}...</td>
                  <td className={`px-4 py-2.5 font-bold ${actor.risk_score >= 75 ? 'text-rose-400' : actor.risk_score >= 40 ? 'text-amber-400' : 'text-emerald-400'}`}>{actor.risk_score}</td>
                  <td className="px-4 py-2.5 text-slate-500">{actor.pii_attempts_last_hour}</td>
                  <td className="px-4 py-2.5 text-slate-500">{actor.injection_attempts_last_hour}</td>
                  <td className="px-4 py-2.5 text-slate-500">{actor.semantic_hits_last_hour}</td>
                  <td className="px-4 py-2.5">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${actor.quarantined ? 'bg-rose-500/15 text-rose-400' : 'bg-emerald-500/15 text-emerald-400'}`}>
                      {actor.quarantined ? 'QUARANTINED' : 'ACTIVE'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="col-span-2 p-5 bg-[#080808] border border-white/8 rounded-2xl space-y-3">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Startup Diagnostics</h3>
          {checks.map((check: any) => (
            <div key={check.name} className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.04]">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-slate-300">{check.name}</span>
                <span className={check.ok ? 'text-emerald-400' : 'text-rose-400'}>{check.ok ? 'PASS' : 'FAIL'}</span>
              </div>
              <p className="text-[11px] text-slate-600">{check.detail}</p>
            </div>
          ))}
          {diagnostics?.certificate && (
            <p className="text-[10px] text-slate-700 font-mono break-all pt-2 border-t border-white/5">{diagnostics.certificate}</p>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ── Enterprise Center Tab ───────────────────────────────────────────────────
function EnterpriseCenterTab() {
  const [models, setModels] = useState<any>(null);
  const [reports, setReports] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [quarantine, setQuarantine] = useState<any[]>([]);
  const [output, setOutput] = useState('');
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [m, r, a, q] = await Promise.all([
        api.get('/api/v2/enterprise/models'),
        api.get('/api/v2/enterprise/reports'),
        api.get('/api/v2/enterprise/alerts'),
        api.get('/api/v2/enterprise/quarantine'),
      ]);
      setModels(m.data);
      setReports(r.data.reports || []);
      setAlerts(a.data.alerts || []);
      setQuarantine(q.data.actors || []);
    } catch { }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const action = async (kind: string) => {
    const payloads: Record<string, any> = {
      firewall: ['/api/v2/enterprise/firewall/rules', { name: 'Block Secret Merger', action: 'quarantine', pattern: 'secret merger', department: 'GLOBAL', severity: 9 }],
      bundle: ['/api/v2/enterprise/policy-bundles/sign', { bundle_name: 'global-sensitive-context-v1', target_scope: 'all-edge-nodes', yaml_content: 'rules: []' }],
      mtls: ['/api/v2/enterprise/mtls/nginx', { server_name: 'sentinel-shield.local', ca_cert_path: '/etc/sentinel/ca.crt', upstream_url: 'http://127.0.0.1:8000' }],
      branding: ['/api/v2/enterprise/branding', { company_name: 'Buyer Organization', product_name: 'Sentinel Shield', primary_color: '#10b981', compliance_frameworks: ['DPDP_2026', 'GDPR', 'FedRAMP'] }],
      anchor: ['/api/v2/enterprise/ledger/anchor', {}],
    };
    try {
      const [url, body] = payloads[kind];
      const res = await api.post(url, body);
      setOutput(JSON.stringify(res.data, null, 2));
      if (kind === 'anchor') load();
    } catch (e: any) {
      setOutput(JSON.stringify(e.response?.data || { error: 'Action failed' }, null, 2));
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Enterprise Center</h2>
          <p className="text-xs text-slate-500">Model ops · alerts · policy sync · mTLS · branding · ledger anchoring</p>
        </div>
        <button onClick={load} className="px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-xs font-bold text-slate-300 hover:bg-white/10">
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard icon={Server} label="Local Models" value={models?.installed_models?.length ?? 0} sub={models?.default_model || 'Vault default'} glow="blue" />
        <StatCard icon={FileText} label="Reports" value={reports.length} sub="Evidence history" glow="emerald" />
        <StatCard icon={Bell} label="CISO Alerts" value={alerts.length} sub="Open alerts" glow={alerts.length ? 'rose' : 'emerald'} />
        <StatCard icon={Lock} label="Quarantined" value={quarantine.length} sub="Contained actors" glow={quarantine.length ? 'rose' : 'blue'} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="p-5 bg-[#080808] border border-white/8 rounded-2xl">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">Model Management Center</h3>
          <p className="text-sm text-white">Default: {models?.default_model || 'llama3.1'}</p>
          <p className="text-xs text-slate-600 mb-3">Ollama: {models?.ollama_base_url || 'http://localhost:11434'}</p>
          <div className="space-y-2 max-h-36 overflow-auto">
            {(models?.installed_models || []).map((m: any) => (
              <div key={m.name} className="flex justify-between text-xs bg-white/5 rounded-xl p-2">
                <span className="text-slate-300">{m.name}</span>
                <span className="text-slate-600">{m.size ? `${Math.round(m.size / 1024 / 1024 / 1024)} GB` : 'local'}</span>
              </div>
            ))}
            {(!models?.installed_models || models.installed_models.length === 0) && <p className="text-xs text-slate-600">No local model inventory available.</p>}
          </div>
        </div>

        <div className="p-5 bg-[#080808] border border-white/8 rounded-2xl">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">Evidence Report History</h3>
          <div className="space-y-2 max-h-44 overflow-auto">
            {reports.slice(0, 5).map((r: any) => (
              <a key={r.name} href={`${API_BASE}${r.download_url}`} target="_blank" className="block text-xs bg-white/5 rounded-xl p-2 hover:bg-white/10">
                <span className="text-slate-300">{r.name}</span>
                <span className="block text-slate-600 font-mono">{r.certificate?.slice(0, 24)}...</span>
              </a>
            ))}
            {reports.length === 0 && <p className="text-xs text-slate-600">No reports generated yet.</p>}
          </div>
        </div>

        <div className="p-5 bg-[#080808] border border-white/8 rounded-2xl">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">CISO Alert Center</h3>
          {alerts.length === 0 ? <p className="text-xs text-slate-600">No open CISO alerts.</p> : alerts.map((a: any) => (
            <div key={a.id} className="text-xs bg-rose-500/10 border border-rose-500/20 rounded-xl p-2 mb-2">
              <p className="text-rose-300 font-bold">{a.severity} · {a.type}</p>
              <p className="text-slate-500 font-mono">{a.actor_hash?.slice(0, 32)}...</p>
            </div>
          ))}
        </div>

        <div className="p-5 bg-[#080808] border border-white/8 rounded-2xl">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">Quarantine Management</h3>
          {quarantine.length === 0 ? <p className="text-xs text-slate-600">No actors currently quarantined.</p> : quarantine.map((q: any) => (
            <div key={q.actor_hash} className="text-xs bg-white/5 rounded-xl p-2 mb-2">
              <p className="text-slate-300 font-mono">{q.actor_hash?.slice(0, 32)}...</p>
              <p className="text-rose-400">{q.quarantine_reason}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-6 gap-3">
        {[
          ['firewall', 'LLM Firewall Rules'],
          ['bundle', 'Policy Sync Signature'],
          ['mtls', 'mTLS Config'],
          ['branding', 'Tenant Branding'],
          ['anchor', 'Ledger Anchor'],
        ].map(([id, label]) => (
          <button key={id} onClick={() => action(id)} className="p-4 bg-white/5 border border-white/10 rounded-2xl text-left hover:bg-white/10">
            <p className="text-xs font-bold text-emerald-300">{label}</p>
          </button>
        ))}
        <div className="p-4 bg-white/5 border border-white/10 rounded-2xl">
          <p className="text-xs font-bold text-slate-300">Browser E2E Proof</p>
          <p className="text-[10px] text-slate-500 font-mono">pnpm smoke:e2e</p>
        </div>
      </div>

      {output && (
        <pre className="p-5 bg-[#080808] border border-white/8 rounded-2xl text-xs text-emerald-300 whitespace-pre-wrap overflow-auto max-h-80">{output}</pre>
      )}
    </motion.div>
  );
}

// ── Universal Proxy Tab ──────────────────────────────────────────────────────
function ProxyTab() {
  const [text, setText] = useState('Patient Aadhaar 2345 6789 0123 and PAN ABCDE1234F wants the merger document reviewed.');
  const [autoRedact, setAutoRedact] = useState(true);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const inspect = async () => {
    setLoading(true);
    try {
      const res = await api.post('/api/v2/proxy/inspect', {
        text,
        source_app: 'localhost-dashboard',
        actor: 'buyer-demo',
        auto_redact: autoRedact,
      });
      setResult(res.data);
    } catch { alert('Proxy inspection failed.'); } finally { setLoading(false); }
  };

  useEffect(() => { inspect(); }, [autoRedact]);

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Universal Proxy Hook</h2>
          <p className="text-xs text-slate-500">Injectable interface for Slack · Teams · CRM · custom apps</p>
        </div>
        <button onClick={() => setAutoRedact(v => !v)}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold border ${autoRedact ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-white/5 border-white/10 text-slate-400'}`}>
          {autoRedact ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
          Auto-Redact
        </button>
      </div>

      <div className="bg-[#080808] border border-white/8 rounded-2xl overflow-hidden">
        <textarea value={text} onChange={e => setText(e.target.value)}
          className="w-full h-32 bg-transparent p-5 text-sm text-slate-200 focus:outline-none resize-none"
          spellCheck={false} />
        <div className="p-4 border-t border-white/8 flex justify-end">
          <button onClick={inspect} disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-black rounded-xl text-xs font-bold transition-all">
            {loading ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
            Inspect
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="p-5 bg-[#080808] border border-white/8 rounded-2xl">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">Before</h3>
          <p className="text-sm text-slate-300 whitespace-pre-wrap min-h-32">{result?.raw_text || text}</p>
        </div>
        <div className="p-5 bg-[#080808] border border-white/8 rounded-2xl">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">After</h3>
          <p className="text-sm text-emerald-300 whitespace-pre-wrap min-h-32">{result?.protected_text || 'Run inspection to preview masked output.'}</p>
        </div>
      </div>

      {result && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard icon={AlertTriangle} label="Sensitivity" value={result.sensitivity_score} sub={result.policy_triggered || 'No policy'} glow={result.sensitivity_score > 7 ? 'rose' : 'amber'} />
          <StatCard icon={Server} label="Route" value={result.route} sub="Gateway decision" glow="blue" />
          <StatCard icon={Zap} label="Pseudonyms" value={result.metadata?.pseudonyms?.length || 0} sub="Context tokens created" glow="purple" />
          <StatCard icon={Globe} label="Source" value={result.source_app} sub="Proxy origin" glow="emerald" />
        </div>
      )}
    </motion.div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState('STAFF');
  const [forcePasswordChange, setForcePasswordChange] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [status, setStatus] = useState<any>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    const t = localStorage.getItem('sentinel_token');
    const user = localStorage.getItem('sentinel_user');
    if (user) {
      try {
        const parsed = JSON.parse(user);
        setRole(parsed.role || 'STAFF');
        setForcePasswordChange(!!parsed.force_password_change);
      } catch { }
    }
    if (t) { setToken(t); fetchStatus(t); }
  }, []);

  const fetchStatus = async (t?: string) => {
    try {
      const cfg = t ? { headers: { Authorization: `Bearer ${t}` } } : {};
      const res = await axios.get(`${API_BASE}/status`, cfg);
      setStatus(res.data);
    } catch { }
  };

  const handleLogin = (t: string, r: string, forceChange: boolean, user: any) => {
    localStorage.setItem('sentinel_user', JSON.stringify({ ...user, role: r, force_password_change: forceChange }));
    setToken(t); setRole(r); setForcePasswordChange(forceChange); fetchStatus(t);
  };

  const logout = async () => {
    try { await api.post('/api/v2/auth/logout'); } catch { }
    localStorage.removeItem('sentinel_token');
    localStorage.removeItem('sentinel_user');
    setToken(null); setRole('STAFF'); setStatus(null); setForcePasswordChange(false);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true);
    const fd = new FormData(); fd.append('file', file);
    try {
      await api.post('/upload', fd);
      fetchStatus();
    } catch { alert('Upload failed — check backend.'); }
    finally { setUploading(false); }
  };

  if (!token) return <LoginScreen onLogin={handleLogin} />;
  if (forcePasswordChange) return <PasswordChangeScreen onChanged={() => {
    setToken(null); setRole('STAFF'); setStatus(null); setForcePasswordChange(false);
  }} />;

  const NAV = [
    { id: 'overview',    icon: Activity,     label: 'Overview' },
    { id: 'vault',       icon: ShieldCheck,  label: 'Vault AI' },
    { id: 'proxy',       icon: Globe,        label: 'Proxy' },
    { id: 'risk',        icon: Bell,         label: 'Oracle Risk' },
    { id: 'audit',       icon: ClipboardList,label: 'Audit Log' },
    { id: 'policy',      icon: BookOpen,     label: 'Policies' },
    { id: 'users',       icon: Users,        label: 'Users', roles: ['SUPER_ADMIN', 'DEPARTMENT_HEAD'] },
    { id: 'compliance',  icon: BarChart3,    label: 'Compliance' },
    { id: 'enterprise',  icon: Settings,     label: 'Enterprise', roles: ['SUPER_ADMIN', 'AUDITOR'] },
  ].filter(n => !n.roles || n.roles.includes(role));

  return (
    <div className="min-h-screen bg-[#030303] text-slate-200 font-sans selection:bg-emerald-500/20 flex">
      {/* Sidebar */}
      <nav className="fixed top-0 left-0 w-60 h-full border-r border-white/[0.06] bg-[#050505] flex flex-col z-50">
        <div className="p-5 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-emerald-500/15 border border-emerald-500/25 rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.15)] overflow-hidden p-1.5">
              <span className="text-sm font-black text-emerald-300 tracking-tight">XT</span>
            </div>
            <div>
              <h1 className="text-sm font-black text-white tracking-tight">SENTINEL <span className="text-emerald-400">SHIELD</span></h1>
              <p className="text-[10px] text-emerald-500/80 font-bold uppercase tracking-widest">BY XAVIRA TECH LABS</p>
            </div>
          </div>
        </div>

        <div className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {NAV.map(item => (
            <button key={item.id} id={`nav-${item.id}`} onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all text-sm ${
                activeTab === item.id
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/15'
                  : 'text-slate-600 hover:text-slate-400 hover:bg-white/[0.03]'}`}>
              <item.icon size={16} />
              <span className="font-medium">{item.label}</span>
            </button>
          ))}
        </div>

        <div className="p-3 border-t border-white/[0.06] space-y-2">
          <div className="px-3 py-2 bg-white/[0.03] rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Live</span>
            </div>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
              { SUPER_ADMIN: 'text-rose-400', DEPARTMENT_HEAD: 'text-purple-400', STAFF: 'text-blue-400', AUDITOR: 'text-amber-400' }[role] || 'text-slate-400'
            }`}>{role}</span>
          </div>
          <button id="logout-btn" onClick={logout}
            className="w-full flex items-center gap-2 px-3.5 py-2 text-slate-700 hover:text-rose-400 hover:bg-rose-500/5 rounded-xl transition-all text-xs">
            <LogOut size={13} /> Sign Out
          </button>
        </div>
      </nav>

      {/* Main */}
      <main className="ml-60 flex-1 p-8 overflow-hidden">
        <header className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-black text-white">
              {NAV.find(n => n.id === activeTab)?.label || 'Dashboard'}
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">Sentinel Shield Enterprise · Xavira Tech Labs</p>
          </div>
          <div className="flex items-center gap-3">
            <button id="refresh-status-btn" onClick={() => fetchStatus()}
              className="p-2.5 bg-white/5 border border-white/10 rounded-xl hover:bg-white/8 transition-all">
              <RefreshCw size={14} className="text-slate-400" />
            </button>
            <label id="upload-doc-btn" className="flex items-center gap-2 px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 rounded-xl text-xs font-bold text-black cursor-pointer transition-all shadow-[0_0_16px_rgba(16,185,129,0.2)]">
              <Upload size={14} />
              {uploading ? 'Ingesting…' : 'Ingest Doc'}
              <input type="file" className="hidden" onChange={handleUpload} />
            </label>
          </div>
        </header>

        <AnimatePresence mode="wait">
          <div key={activeTab}>
            {activeTab === 'overview'   && <OverviewTab status={status} />}
            {activeTab === 'vault'      && <VaultTab role={role} />}
            {activeTab === 'proxy'      && <ProxyTab />}
            {activeTab === 'risk'       && <RiskTab />}
            {activeTab === 'audit'      && <AuditLogTab />}
            {activeTab === 'policy'     && <PolicyTab role={role} />}
            {activeTab === 'users'      && <UsersTab role={role} />}
            {activeTab === 'compliance' && <ComplianceTab />}
            {activeTab === 'enterprise' && <EnterpriseCenterTab />}
          </div>
        </AnimatePresence>
      </main>
    </div>
  );
}
