'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const API_BASE = 'https://sentinel-shield-ww9d.onrender.com';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    // If already logged in, redirect to dashboard
    if (localStorage.getItem('sentinel_token')) {
      router.push('/');
    }
  }, [router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const resp = await fetch(`${API_BASE}/api/v2/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await resp.json();

      if (resp.ok && data.access_token) {
        localStorage.setItem('sentinel_token', data.access_token);
        localStorage.setItem('sentinel_user', JSON.stringify(data.user));
        router.push('/');
      } else {
        setError(data.detail || 'Access Denied: Invalid Security Credentials');
      }
    } catch {
      setError('Sentinel Engine Offline: Connection to Cloud Failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b1120] flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background Pulse Effect */}
      <div className="absolute top-[-20%] left-[-20%] w-[140%] h-[140%] bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.05)_0%,transparent_60%)] animate-pulse"></div>
      
      <div className="w-full max-w-md bg-[#1e293b]/50 backdrop-blur-xl border border-[#334155] rounded-2xl p-8 shadow-2xl relative z-10">
        <div className="text-center mb-10">
          <div className="inline-block p-4 rounded-full bg-[#38bdf8]/10 mb-4 border border-[#38bdf8]/20">
            <svg className="w-12 h-12 text-[#38bdf8]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h1 className="text-3xl font-extrabold text-[#f8fafc] tracking-tight">Sentinel Shield</h1>
          <p className="text-[#38bdf8] mt-2 text-xs uppercase tracking-widest font-bold opacity-80">BY XAVIRA TECH LABS</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-xs p-4 rounded-lg text-center font-medium animate-shake">
              ⚠️ {error}
            </div>
          )}

          <div>
            <label className="block text-[#e2e8f0] text-sm font-bold mb-2 ml-1">Identity (Organization Email)</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] text-white p-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#38bdf8]/50 transition duration-300"
              placeholder="e.g. vishnu@enterprise.com"
              required
            />
          </div>

          <div>
            <label className="block text-[#e2e8f0] text-sm font-bold mb-2 ml-1">Security Vault Key</label>
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
            {loading ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-[#020617]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                AUTHENTICATING...
              </span>
            ) : (
              "SIGN INTO GATEWAY"
            )}
          </button>
        </form>

        <div className="mt-8 text-center text-[#94a3b8] text-sm group">
          Need Access? <Link href="/register" className="text-[#38bdf8] font-bold hover:underline">Create Pro Account</Link>
        </div>

        <div className="mt-8 text-center text-[#475569] text-xs">
          Air-Gapped Node ID: 299-GLOBAL-SHIELD<br/>
          Protected by Elliptic Curve Cryptography
        </div>
      </div>
    </div>
  );
}
