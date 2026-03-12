'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ShieldCheck,
    ShieldAlert,
    Upload,
    Search,
    Lock,
    Activity,
    FileText,
    AlertTriangle,
    Send,
    Loader2,
    ChevronRight
} from 'lucide-react';
import axios from 'axios';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts';

const API_BASE = 'http://localhost:8000';

const riskData = [
    { name: '09:00', risk: 2.4 },
    { name: '10:00', risk: 3.1 },
    { name: '11:00', risk: 1.8 },
    { name: '12:00', risk: 4.5 },
    { name: '13:00', risk: 3.2 },
    { name: '14:00', risk: 5.9 },
    { name: '15:00', risk: 4.1 },
];

export default function Dashboard() {
    const [activeTab, setActiveTab] = useState('overview');
    const [isUploading, setIsUploading] = useState(false);
    const [query, setQuery] = useState('');
    const [chatHistory, setChatHistory] = useState<any[]>([]);
    const [status, setStatus] = useState<any>(null);
    const [loadingChat, setLoadingChat] = useState(false);

    useEffect(() => {
        fetchStatus();
    }, []);

    const fetchStatus = async () => {
        try {
            const res = await axios.get(`${API_BASE}/status`);
            setStatus(res.data);
        } catch (e) {
            console.error("Backend not reachable");
        }
    };

    const handleFileUpload = async (e: any) => {
        const file = e.target.files[0];
        if (!file) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            await axios.post(`${API_BASE}/upload`, formData);
            fetchStatus();
        } catch (err) {
            alert("Upload failed. Make sure backend is running.");
        } finally {
            setIsUploading(false);
        }
    };

    const handleAsk = async () => {
        if (!query.trim()) return;
        setLoadingChat(true);
        const userMsg = { role: 'user', content: query };
        setChatHistory([...chatHistory, userMsg]);
        setQuery('');

        try {
            const res = await axios.post(`${API_BASE}/ask`, { prompt: query });
            setChatHistory(prev => [...prev, { role: 'bot', ...res.data }]);
        } catch (err) {
            setChatHistory(prev => [...prev, { role: 'bot', answer: "Error: No response from Sentinel. Is the engine running?", risk_level: 'ERROR' }]);
        } finally {
            setLoadingChat(false);
        }
    };

    return (
        <div className="min-h-screen bg-black text-slate-200 font-sans selection:bg-emerald-500/30">
            {/* Sidebar / Nav */}
            <nav className="fixed top-0 left-0 w-64 h-full border-r border-white/10 bg-[#050505] p-6 z-50">
                <div className="flex items-center gap-3 mb-10">
                    <div className="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.3)]">
                        <Lock className="text-white w-6 h-6" />
                    </div>
                    <h1 className="text-xl font-bold tracking-tight text-white">SENTINEL<span className="text-emerald-500">VAULT</span> <span className="text-[10px] ml-1 opacity-50">V1</span></h1>
                </div>

                <div className="space-y-2">
                    {[
                        { id: 'overview', icon: Activity, label: 'Security Overview' },
                        { id: 'chat', icon: Send, label: 'Vault Intelligence' },
                        { id: 'files', icon: FileText, label: 'Document Audit' },
                        { id: 'settings', icon: ShieldCheck, label: 'Access Control' },
                    ].map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setActiveTab(item.id)}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === item.id
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : 'text-slate-500 hover:bg-white/5 hover:text-slate-300'
                                }`}
                        >
                            <item.icon size={20} />
                            <span className="font-medium">{item.label}</span>
                        </button>
                    ))}
                </div>

                <div className="absolute bottom-8 left-6 right-6">
                    <div className="p-4 bg-white/5 rounded-2xl border border-white/10">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">System Status</span>
                        </div>
                        <p className="text-sm text-slate-300">Vault Core: 100% Secure</p>
                    </div>
                </div>
            </nav>

            {/* Main Content */}
            <main className="pl-64 pt-8 pb-12 transition-all">
                <div className="max-w-6xl mx-auto px-8">
                    <header className="flex justify-between items-end mb-12">
                        <div>
                            <h2 className="text-3xl font-bold text-white mb-2">Enterprise Intelligence</h2>
                            <p className="text-slate-500">Air-gapped security monitoring & RAG insights.</p>
                        </div>
                        <div className="flex gap-4">
                            <label className="cursor-pointer bg-white text-black px-6 py-2.5 rounded-full font-bold hover:bg-emerald-400 transition-all flex items-center gap-2 shadow-lg shadow-white/5">
                                <Upload size={18} />
                                {isUploading ? 'Analyzing...' : 'Ingest Document'}
                                <input type="file" className="hidden" onChange={handleFileUpload} />
                            </label>
                        </div>
                    </header>

                    <AnimatePresence mode="wait">
                        {activeTab === 'overview' && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="grid grid-cols-12 gap-6"
                            >
                                {/* Stats */}
                                <div className="col-span-4 p-6 bg-[#0a0a0a] border border-white/10 rounded-3xl relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 blur-[60px] group-hover:bg-emerald-500/20 transition-all" />
                                    <p className="text-slate-500 font-bold text-xs uppercase tracking-widest mb-4">Total Documents</p>
                                    <p className="text-5xl font-bold text-white mb-2">{status?.documents_count || 0}</p>
                                    <div className="flex items-center gap-2 text-emerald-500 text-sm font-medium">
                                        <ShieldCheck size={16} /> Verified Security
                                    </div>
                                </div>

                                <div className="col-span-4 p-6 bg-[#0a0a0a] border border-white/10 rounded-3xl relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 blur-[60px]" />
                                    <p className="text-slate-500 font-bold text-xs uppercase tracking-widest mb-4">Autonomous Monitor</p>
                                    <p className="text-5xl font-bold text-rose-500 mb-2">LIVE</p>
                                    <div className="flex items-center gap-2 text-rose-400 text-sm font-medium">
                                        <Activity size={16} className="animate-pulse" /> 24/7 Watchdog Active
                                    </div>
                                </div>

                                <div className="col-span-4 p-6 bg-[#0a0a0a] border border-white/10 rounded-3xl relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 blur-[60px]" />
                                    <p className="text-slate-500 font-bold text-xs uppercase tracking-widest mb-4">Air-Gap Status</p>
                                    <p className="text-5xl font-bold text-purple-400 mb-2">100%</p>
                                    <div className="flex items-center gap-2 text-purple-400 text-sm font-medium">
                                        <Lock size={16} /> Zero Network Leakage
                                    </div>
                                </div>

                                {/* Chart */}
                                <div className="col-span-8 p-8 bg-[#0a0a0a] border border-white/10 rounded-3xl min-h-[400px]">
                                    <h3 className="text-lg font-bold text-white mb-8">Security Risk Propagation</h3>
                                    <div className="h-[300px]">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <AreaChart data={riskData}>
                                                <defs>
                                                    <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                                    </linearGradient>
                                                </defs>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                                                <XAxis dataKey="name" stroke="#555" fontSize={12} tickLine={false} axisLine={false} />
                                                <YAxis stroke="#555" fontSize={12} tickLine={false} axisLine={false} />
                                                <Tooltip
                                                    contentStyle={{ backgroundColor: '#111', border: '1px solid #333', borderRadius: '12px' }}
                                                    itemStyle={{ color: '#10b981' }}
                                                />
                                                <Area type="monotone" dataKey="risk" stroke="#10b981" fillOpacity={1} fill="url(#colorRisk)" strokeWidth={3} />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>

                                <div className="col-span-4 p-8 bg-[#0a0a0a] border border-white/10 rounded-3xl">
                                    <h3 className="text-lg font-bold text-white mb-6">Recent Findings</h3>
                                    <div className="space-y-4">
                                        {[
                                            { label: 'AWS Secret Detected', risk: 'HIGH', time: '2m ago' },
                                            { label: 'Unmasked PII found', risk: 'MED', time: '1h ago' },
                                            { label: 'SSH Key Exposed', risk: 'CRIT', time: '4h ago' },
                                        ].map((leak, i) => (
                                            <div key={i} className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/5">
                                                <div>
                                                    <p className="text-sm font-bold text-slate-200">{leak.label}</p>
                                                    <p className="text-xs text-slate-500">{leak.time}</p>
                                                </div>
                                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${leak.risk === 'CRIT' ? 'bg-rose-500/20 text-rose-400' : 'bg-orange-500/20 text-orange-400'
                                                    }`}>
                                                    {leak.risk}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'chat' && (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.98 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.98 }}
                                className="flex flex-col h-[75vh] bg-[#0a0a0a] border border-white/10 rounded-3xl overflow-hidden shadow-2xl"
                            >
                                <div className="p-6 border-b border-white/10 flex justify-between items-center bg-[#070707]">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                                            <ShieldCheck className="text-emerald-500 w-5 h-5" />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-white">Sentinel AI Intelligence</h3>
                                            <p className="text-xs text-slate-500">Operational with Llama-3 (Local)</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex-1 overflow-y-auto p-8 space-y-6 scrollbar-hide">
                                    {chatHistory.length === 0 && (
                                        <div className="h-full flex flex-col items-center justify-center text-center">
                                            <div className="w-16 h-16 bg-white/5 rounded-3xl flex items-center justify-center mb-6 border border-white/10">
                                                <Lock className="text-slate-400" size={32} />
                                            </div>
                                            <h4 className="text-xl font-bold text-white mb-2">Secure Query Interface</h4>
                                            <p className="text-slate-500 max-w-sm">Ask anything about your internal documents. All processing is kept strictly local and air-gapped.</p>
                                        </div>
                                    )}
                                    {chatHistory.map((msg, i) => (
                                        <motion.div
                                            initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            key={i}
                                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                        >
                                            <div className={`max-w-[80%] p-4 rounded-2xl ${msg.role === 'user'
                                                ? 'bg-emerald-600 text-white rounded-tr-none shadow-lg shadow-emerald-900/10'
                                                : 'bg-white/5 border border-white/10 text-slate-200 rounded-tl-none'
                                                }`}>
                                                {msg.role === 'bot' && (
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold bg-white/10 ${msg.risk_level === 'HIGH' ? 'bg-rose-500/20 text-rose-400' : 'text-emerald-400'
                                                            }`}>
                                                            Risk: {msg.risk_level || 'CLEAN'}
                                                        </span>
                                                    </div>
                                                )}
                                                <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{msg.answer || msg.content}</p>
                                                {msg.sources && (
                                                    <div className="mt-3 pt-3 border-t border-white/10 flex gap-2">
                                                        {msg.sources.map((src: string, j: number) => (
                                                            <span key={j} className="text-[10px] bg-white/5 px-2 py-1 rounded text-slate-500 italic">
                                                                {src}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </motion.div>
                                    ))}
                                    {loadingChat && (
                                        <div className="flex justify-start">
                                            <div className="bg-white/5 border border-white/10 p-4 rounded-2xl flex items-center gap-3">
                                                <Loader2 className="animate-spin text-emerald-500" size={18} />
                                                <span className="text-sm text-slate-400">Sentinel is analyzing vault...</span>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="p-6 bg-[#070707] border-t border-white/10">
                                    <div className="relative flex items-center">
                                        <input
                                            type="text"
                                            value={query}
                                            onChange={(e) => setQuery(e.target.value)}
                                            onKeyPress={(e) => e.key === 'Enter' && handleAsk()}
                                            placeholder="Type your security query..."
                                            className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-6 pr-16 text-white focus:outline-none focus:border-emerald-500/50 transition-all placeholder:text-slate-600"
                                        />
                                        <button
                                            onClick={handleAsk}
                                            className="absolute right-3 w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center text-black hover:bg-emerald-400 transition-all shadow-lg"
                                        >
                                            <Send size={18} />
                                        </button>
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}
