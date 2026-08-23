import React, { useState } from "react";
import { Shield, Lock, ArrowRight, AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";
import { GoogleLogin } from '@react-oauth/google';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

interface LoginProps {
  onLogin: (token: string, email: string) => void;
}

export default function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (res.ok) {
        const data = await res.json();
        onLogin(data.access_token, data.email);
      } else {
        const errData = await res.json();
        setError(errData.detail || "Invalid login credentials.");
      }
    } catch (err) {
      setError("Unable to connect to the server.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async (credential: string) => {
    setError("");
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/login/google`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ token: credential }),
      });

      if (res.ok) {
        const data = await res.json();
        onLogin(data.access_token, data.email);
      } else {
        const errData = await res.json();
        setError(errData.detail || "Google Login failed.");
      }
    } catch (err) {
      setError("Unable to connect to the server.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-[#030712] items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 bg-[#070b19] border border-slate-800 rounded-2xl flex items-center justify-center mb-4">
            <Shield className="w-8 h-8 text-accentcyan" />
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-widest uppercase">ScamCheck</h1>
          <p className="text-slate-400 text-sm mt-2 font-mono">AUTHORIZED PERSONNEL ONLY</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-[#070b19] border border-slate-800/80 p-6 rounded-2xl space-y-5 shadow-2xl">
          {error && (
            <div className="bg-accentred/10 border border-accentred/30 p-3 rounded-lg flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-accentred flex-shrink-0" />
              <p className="text-xs text-accentred font-mono">{error}</p>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-[10px] font-bold font-mono text-slate-400 block uppercase">Email Address</label>
            <div className="relative">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@scamcheck.io"
                className="w-full bg-slate-950 border border-slate-900 rounded-lg p-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-accentcyan transition-colors"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-bold font-mono text-slate-400 block uppercase">Password</label>
            <div className="relative">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-950 border border-slate-900 rounded-lg p-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-accentcyan transition-colors"
                required
              />
              <Lock className="w-4 h-4 text-slate-600 absolute right-3 top-3.5" />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-accentcyan to-accentemerald text-darkbg font-bold py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 mt-4"
          >
            {isLoading ? "Authenticating..." : "Access System"}
            {!isLoading && <ArrowRight className="w-4 h-4" />}
          </button>
          
          <div className="relative flex py-2 items-center">
            <div className="flex-grow border-t border-slate-800"></div>
            <span className="flex-shrink-0 mx-4 text-slate-500 text-[10px] font-mono">OR</span>
            <div className="flex-grow border-t border-slate-800"></div>
          </div>

          <div className="w-full flex justify-center">
            <GoogleLogin
              onSuccess={credentialResponse => {
                if (credentialResponse.credential) {
                  handleGoogleLogin(credentialResponse.credential);
                }
              }}
              onError={() => {
                setError("Google Login failed.");
              }}
              theme="filled_black"
              shape="pill"
            />
          </div>
        </form>

        <div className="mt-8 text-center text-[10px] font-mono text-slate-600">
          <p>ScamCheck Security Copilot &copy; 2026</p>
        </div>
      </motion.div>
    </div>
  );
}
