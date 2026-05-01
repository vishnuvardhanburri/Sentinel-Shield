'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [dept, setDept] = useState('GENERAL');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const resp = await fetch(`${API_BASE}/api/v2/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, department: dept })
      });

      const data = await resp.json();

      if (resp.ok) {
        setSuccess('Sentinel Identity Registered: You can now sign in.');
        setTimeout(() => router.push('/login'), 2000);
      } else {
        setError(data.detail || 'Identity Conflict: Registration Failed');
      }
    } catch {
      setError('Sentinel Engine Offline: Connection to Cloud Failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b1120] flex items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute top-[-20%] left-[-20%] w-[140%] h-[140%] bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.05)_0%,transparent_60%)] animate-pulse"></div>
      
      <div className="w-full max-w-md bg-[#1e293b]/50 backdrop-blur-xl border border-[#334155] rounded-2xl p-8 shadow-2xl relative z-10">
        <div className="text-center mb-10">
          <div className="inline-block p-4 rounded-full bg-[#38bdf8]/10 mb-4 border border-[#38bdf8]/20">
            <svg className="w-12 h-12 text-[#38bdf8]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </div>
          <h1 className="text-3xl font-extrabold text-[#f8fafc] tracking-tight">Create Pro Account</h1>
          <p className="text-[#38bdf8] mt-2 text-xs uppercase tracking-widest font-bold opacity-80">BY XAVIRA TECH LABS</p>
        </div>

        <form onSubmit={handleRegister} className="space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-xs p-4 rounded-lg text-center font-medium">
              ⚠️ {error}
            </div>
          )}

          {success && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs p-4 rounded-lg text-center font-medium">
              ✅ {success}
            </div>
          )}

          <div>
            <label className="block text-[#e2e8f0] text-sm font-bold mb-2 ml-1">Work Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] text-white p-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#38bdf8]/50 transition duration-300"
              placeholder="name@company.com"
              required
            />
          </div>

          <div>
            <label className="block text-[#e2e8f0] text-sm font-bold mb-2 ml-1">Department</label>
            <select
              value={dept}
              onChange={(e) => setDept(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] text-white p-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#38bdf8]/50 transition duration-300"
            >
              <option value="GENERAL">General Access</option>
              <option value="IT">IT & Infrastructure</option>
              <option value="HR">Human Resources</option>
              <option value="FINANCE">Finance & Legal</option>
              <option value="SECURITY">Security Operations</option>
            </select>
          </div>

          <div>
            <label className="block text-[#e2e8f0] text-sm font-bold mb-2 ml-1">Create Vault Key</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] text-white p-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#38bdf8]/50 transition duration-300"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#38bdf8] hover:bg-[#7dd3fc] text-[#020617] font-bold py-4 rounded-xl transition duration-300 shadow-xl disabled:opacity-50 flex items-center justify-center"
          >
            {loading ? "REGISTERING..." : "ACTIVATE PRO SHIELD"}
          </button>
        </form>

        <div className="mt-8 text-center text-[#94a3b8] text-sm">
          Already have keys? <Link href="/login" className="text-[#38bdf8] font-bold hover:underline">Sign into Gateway</Link>
        </div>
      </div>
    </div>
  );
}
