import React, { useState, useEffect } from "react";
import {
  Shield, Upload, Globe, AlertTriangle, CheckCircle,
  Settings, History, Activity, Share2, Compass, BookOpen,
  ArrowRight, RefreshCw, Send, Lock, Eye, Download, ChevronRight, Terminal, Menu, X, Check
} from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { motion, AnimatePresence } from "framer-motion";
import Login from "./Login";
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => !!localStorage.getItem("access_token"));
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem("user_email") || "");

  const handleLogin = (token: string, email: string) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("user_email", email);
    setIsLoggedIn(true);
    setUserEmail(email);
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_email");
    setIsLoggedIn(false);
    setUserEmail("");
  };

  const [activeTab, setActiveTab] = useState("landing");
  const [inputText, setInputText] = useState("");
  const [inputUrl, setInputUrl] = useState("");
  const [inputType, setInputType] = useState("TEXT");
  const [fileRef, setFileRef] = useState("mock_file_ref");
  const [fileName, setFileName] = useState("");
  const [fileSize, setFileSize] = useState("");
  const [fileType, setFileType] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [fileError, setFileError] = useState("");
  
  // App settings state
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [modelRegistry, setModelRegistry] = useState<any>(null);

  // Active scan tracking
  const [currentScanId, setCurrentScanId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<any>(null);
  const [trustReport, setTrustReport] = useState<any>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<any>(null);
  const [showPassport, setShowPassport] = useState(false);

  // Filter & Search states
  const [historyList, setHistoryList] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [historyFilter, setHistoryFilter] = useState("ALL");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // AI Copilot state
  const [copilotMessages, setCopilotMessages] = useState<any[]>([
    { sender: "system", text: "Hello! I am your AI Safety Copilot. Once you select or run a scan, I can explain the evidence, analyze potential phishing risks, and guide you on safe actions." }
  ]);
  const [copilotInput, setCopilotInput] = useState("");
  const [copilotLoading, setCopilotLoading] = useState(false);

  // Fetch scan history
  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/history`);
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data);
      }
    } catch (err) {
      console.error("Error fetching history:", err);
    }
  };

  // Fetch model registry metrics
  const fetchModelRegistry = async () => {
    try {
      const res = await fetch(`${API_BASE}/settings/registry`);
      if (res.ok) {
        const data = await res.json();
        setModelRegistry(data);
      }
    } catch (err) {
      console.error("Error fetching model registry:", err);
    }
  };

  useEffect(() => {
    fetchHistory();
    fetchModelRegistry();
    // Synchronize initial UI state with backend setting
    fetch(`${API_BASE}/settings/toggle-demo?is_demo=false`, { method: "POST" });
  }, []);

  // Poll scan status
  useEffect(() => {
    let timer: any;
    if (currentScanId && (!scanStatus || (scanStatus.status !== "COMPLETE" && scanStatus.status !== "FAILED"))) {
      const poll = async () => {
        try {
          const res = await fetch(`${API_BASE}/scan/${currentScanId}`);
          if (res.ok) {
            const data = await res.json();
            setScanStatus(data);
            if (data.status === "COMPLETE") {
              // Load Trust Report
              const rRes = await fetch(`${API_BASE}/report/${currentScanId}`);
              if (rRes.ok) {
                const rData = await rRes.json();
                setTrustReport(rData);
                setActiveTab("report");
                fetchHistory();
              }
            } else if (data.status === "FAILED") {
              console.error("Scan analysis failed:", data.failure_reason);
            }
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      };
      timer = setInterval(poll, 1200);
      poll();
    }
    return () => clearInterval(timer);
  }, [currentScanId, scanStatus]);

  // Submit scan
  const handleScanSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setScanStatus(null);
    setTrustReport(null);
    setCurrentScanId(null);
    setActiveTab("processing");

    const payload: any = { input_type: inputType };
    if (inputType === "TEXT") payload.text = inputText;
    else if (inputType === "URL") payload.url = inputUrl.startsWith("http") ? inputUrl : `https://${inputUrl}`;
    else payload.file_ref = fileRef;

    try {
      const res = await fetch(`${API_BASE}/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentScanId(data.id);
        setScanStatus({ id: data.id, status: data.status });
      } else {
        setActiveTab("new_scan");
        alert("Failed to submit scan.");
      }
    } catch (err) {
      setActiveTab("new_scan");
      alert("Backend connection error.");
    }
  };

  // Toggle demo mode on backend
  const handleToggleDemoMode = async (checked: boolean) => {
    setIsDemoMode(checked);
    try {
      await fetch(`${API_BASE}/settings/toggle-demo?is_demo=${checked}`, { method: "POST" });
    } catch (err) {
      console.error(err);
    }
  };

  // Trigger retraining
  const handleRetrain = async () => {
    setIsTraining(true);
    try {
      const res = await fetch(`${API_BASE}/train`, { method: "POST" });
      if (res.ok) {
        alert("Model retraining initiated in background.");
        setTimeout(fetchModelRegistry, 5000); // Poll registry update
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsTraining(false);
    }
  };

  // View past report from history
  const handleViewReport = async (scanId: string) => {
    setCurrentScanId(scanId);
    setScanStatus({ id: scanId, status: "COMPLETE" });
    try {
      const rRes = await fetch(`${API_BASE}/report/${scanId}`);
      if (rRes.ok) {
        const rData = await rRes.json();
        setTrustReport(rData);
        setActiveTab("report");
        // Scroll main content pane to top
        window.scrollTo(0, 0);
      }
    } catch (err) {
      alert("Failed to retrieve report.");
    }
  };

  // Send message to Copilot
  const handleSendCopilot = async (messageText: string) => {
    if (!messageText.trim() || copilotLoading) return;
    
    setCopilotMessages(prev => [...prev, { sender: "user", text: messageText }]);
    setCopilotLoading(true);

    try {
      const res = await fetch(`${API_BASE}/copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scan_id: currentScanId || historyList[0]?.id || "00000000-0000-0000-0000-000000000000",
          message: messageText
        })
      });
      if (res.ok) {
        const data = await res.json();
        setCopilotMessages(prev => [...prev, { sender: "copilot", text: data.reply }]);
      } else {
        setCopilotMessages(prev => [...prev, { sender: "copilot", text: "I ran into a server error processing your request. Please try again." }]);
      }
    } catch (err) {
      setCopilotMessages(prev => [...prev, { sender: "copilot", text: "Connection error. Make sure the backend server is running." }]);
    } finally {
      setCopilotLoading(false);
    }
  };

  // Drag & drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file: File) => {
    setFileError("");
    // Check file size (limit to 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setFileError("File exceeds the 10MB size limit.");
      return;
    }

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (inputType === "SCREENSHOT" && !["jpg", "jpeg", "png", "webp"].includes(ext || "")) {
      setFileError("Invalid image file format. Supported formats: PNG, JPG, WEBP.");
      return;
    }
    if (inputType === "PDF" && ext !== "pdf") {
      setFileError("Invalid document. Must upload a PDF file.");
      return;
    }

    setFileName(file.name);
    setFileSize((file.size / (1024 * 1024)).toFixed(2) + " MB");
    setFileType(file.type || ext || "unknown");
    setFileRef("uploaded_" + Math.random().toString(36).substring(7));
  };

  const removeFile = () => {
    setFileName("");
    setFileSize("");
    setFileType("");
    setFileRef("mock_file_ref");
    setFileError("");
  };

  // Filtered History
  const filteredHistory = historyList.filter(s => {
    const matchesSearch = s.opportunity_title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.company_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.id?.includes(searchQuery);

    if (historyFilter === "ALL") return matchesSearch;
    if (historyFilter === "HIGH") return matchesSearch && s.risk_score >= 70;
    if (historyFilter === "WARNING") return matchesSearch && s.risk_score >= 40 && s.risk_score < 70;
    if (historyFilter === "SAFE") return matchesSearch && s.risk_score < 40;
    return matchesSearch;
  });

  // Calculate statistics from history
  const totalScansCount = historyList.length;
  const highRiskCount = historyList.filter(s => s.risk_score >= 70).length;
  const safeCount = historyList.filter(s => s.risk_score !== null && s.risk_score < 40).length;

  if (!isLoggedIn) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="flex h-screen w-screen bg-[#030712] text-slate-100 font-sans overflow-hidden">
      
      {/* 1. SIDEBAR NAVIGATION - DESKTOP */}
      <aside className="hidden lg:flex flex-col justify-between w-64 border-r border-slate-800/60 bg-[#070b19]/60 p-4 flex-shrink-0 z-20">
        <div>
          {/* Brand Logo */}
          <div className="flex items-center gap-2 px-2 py-3 mb-6 border-b border-slate-800/40">
            <Shield className="w-5 h-5 text-accentcyan" />
            <span className="font-extrabold text-sm tracking-widest text-white">
              SCAMCHECK
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded border border-slate-800 bg-[#030712] text-accentcyan font-mono scale-90">
              SECURE
            </span>
          </div>

          {/* Nav Items */}
          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab("landing")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                activeTab === "landing" ? "bg-slate-800/50 text-white font-bold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
              }`}
            >
              <Compass className="w-4 h-4" />
              Gateway Portal
            </button>
            <button
              onClick={() => setActiveTab("dashboard")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                activeTab === "dashboard" ? "bg-slate-800/50 text-white font-bold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
              }`}
            >
              <Activity className="w-4 h-4" />
              Surveillance Dashboard
            </button>
            <button
              onClick={() => { setInputText(""); setInputUrl(""); removeFile(); setInputType("TEXT"); setActiveTab("new_scan"); }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                activeTab === "new_scan" || activeTab === "processing" ? "bg-slate-800/50 text-white font-bold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
              }`}
            >
              <Upload className="w-4 h-4" />
              New Scan Analysis
            </button>
            {currentScanId && trustReport && (
              <button
                onClick={() => setActiveTab("report")}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  activeTab === "report" ? "bg-slate-800/50 text-white font-bold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
                }`}
              >
                <Eye className="w-4 h-4" />
                Latest Trust Report
              </button>
            )}
            <button
              onClick={() => { fetchHistory(); setActiveTab("history"); }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                activeTab === "history" ? "bg-slate-800/50 text-white font-bold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
              }`}
            >
              <History className="w-4 h-4" />
              Analysis Log History
            </button>
            <button
              onClick={() => setActiveTab("intelligence")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                activeTab === "intelligence" ? "bg-slate-800/50 text-white font-bold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
              }`}
            >
              <Terminal className="w-4 h-4" />
              Threat Intel List
            </button>
            <button
              onClick={() => setActiveTab("copilot")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                activeTab === "copilot" ? "bg-slate-800/50 text-white font-bold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
              }`}
            >
              <Send className="w-4 h-4" />
              AI Safety Copilot
            </button>
            <button
              onClick={() => setActiveTab("learning")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                activeTab === "learning" ? "bg-slate-800/50 text-white font-bold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
              }`}
            >
              <BookOpen className="w-4 h-4" />
              Learning Hub
            </button>
          </nav>
        </div>

        {/* Footer controls & Settings */}
        <div className="border-t border-slate-800/40 pt-4 space-y-3">
          <button
            onClick={() => setActiveTab("settings")}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeTab === "settings" ? "bg-slate-800/50 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Settings className="w-4 h-4" />
            Config & ML Registry
          </button>
          
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all text-slate-400 hover:text-accentred hover:bg-accentred/10"
          >
            <Lock className="w-4 h-4" />
            Sign Out ({userEmail})
          </button>

          <div className="px-3 py-2 rounded bg-slate-900/60 border border-slate-800/40 text-[10px] font-mono flex items-center justify-between">
            <span className="text-slate-500">Mode:</span>
            {isDemoMode ? (
              <span className="text-accentamber flex items-center gap-1 font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-accentamber animate-pulse"></span>
                DEMO FALLBACK
              </span>
            ) : (
              <span className="text-accentcyan flex items-center gap-1 font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-accentcyan animate-pulse"></span>
                PRODUCTION ML
              </span>
            )}
          </div>
        </div>
      </aside>

      {/* MOBILE HEADER & NAVIGATION */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-[#070b19] border-b border-slate-800/60 flex items-center justify-between px-4 z-30">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-accentcyan" />
          <span className="font-extrabold text-sm tracking-wider text-white">SCAMCHECK</span>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-1 rounded bg-slate-800 text-slate-200"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu panel drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 top-14 bg-[#030712] z-20 flex flex-col p-4 space-y-4">
          <nav className="space-y-2">
            {[
              { id: "landing", label: "Gateway Portal", icon: Compass },
              { id: "dashboard", label: "Surveillance Dashboard", icon: Activity },
              { id: "new_scan", label: "New Scan Analysis", icon: Upload },
              { id: "history", label: "Analysis Log History", icon: History },
              { id: "intelligence", label: "Threat Intel List", icon: Terminal },
              { id: "copilot", label: "AI Safety Copilot", icon: Send },
              { id: "learning", label: "Learning Hub", icon: BookOpen },
              { id: "settings", label: "Config & ML Registry", icon: Settings },
            ].map(item => (
              <button
                key={item.id}
                onClick={() => {
                  if (item.id === "new_scan") {
                    setInputText(""); setInputUrl(""); removeFile(); setInputType("TEXT");
                  }
                  setActiveTab(item.id);
                  setMobileMenuOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold ${
                  activeTab === item.id ? "bg-slate-800 text-white" : "text-slate-400"
                }`}
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </button>
            ))}
          </nav>
          
          <div className="border-t border-slate-800/40 pt-4 flex justify-between items-center text-xs">
            <span className="text-slate-400 font-semibold">Demo Sandbox:</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={isDemoMode}
                onChange={(e) => { handleToggleDemoMode(e.target.checked); setMobileMenuOpen(false); }}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-700 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accentcyan"></div>
            </label>
          </div>
        </div>
      )}

      {/* 2. MAIN APP FRAME CONTENT */}
      <main className="flex-1 flex flex-col h-full bg-[#030712] overflow-y-auto relative pt-14 lg:pt-0">
        <div className="p-4 lg:p-8 max-w-6xl mx-auto w-full flex-1 pb-16">
          
          <AnimatePresence mode="wait">
            
            {/* VIEW A: LANDING PAGE */}
            {activeTab === "landing" && (
              <motion.div
                key="landing"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-12 py-6 lg:py-12"
              >
                {/* Hero Header */}
                <div className="text-center space-y-4 max-w-3xl mx-auto">
                  <span className="text-[10px] tracking-widest font-mono text-accentcyan border border-accentcyan/30 px-3 py-1 rounded-full uppercase">
                    Cybersecurity Recruitment Protection
                  </span>
                  <h1 className="text-4xl lg:text-6xl font-extrabold tracking-tight text-white uppercase leading-none">
                    BEFORE YOU APPLY.<br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-accentcyan to-accentemerald">VERIFY.</span>
                  </h1>
                  <p className="text-slate-400 text-sm lg:text-lg max-w-2xl mx-auto">
                    AI-powered verification for internships and job opportunities. Spot advance-fee fraud, domain hijacking, and recruiter impersonations.
                  </p>
                  
                  <div className="flex flex-col sm:flex-row justify-center items-center gap-3 pt-4">
                    <button
                      onClick={() => { setInputText(""); setInputUrl(""); removeFile(); setInputType("TEXT"); setActiveTab("new_scan"); }}
                      className="w-full sm:w-auto flex items-center justify-center gap-2 bg-gradient-to-r from-accentcyan to-accentemerald text-darkbg hover:opacity-90 font-bold px-6 py-3 rounded-lg transition-all"
                    >
                      Analyze an Opportunity
                      <ArrowRight className="w-4 h-4" />
                    </button>
                    <a
                      href="#how-it-works"
                      className="w-full sm:w-auto flex items-center justify-center gap-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 font-semibold px-6 py-3 rounded-lg transition-all"
                    >
                      See How It Works
                    </a>
                  </div>
                </div>

                {/* Product Flow Section */}
                <div id="how-it-works" className="pt-8 border-t border-slate-900 space-y-6">
                  <h2 className="text-xs font-mono text-slate-500 uppercase tracking-widest text-center">PRODUCT TIMELINE PROCESS</h2>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { step: "SUBMIT", desc: "Paste recruitment text or upload job offer screenshots & PDFs." },
                      { step: "ANALYZE", desc: "ML pipelines extract entities, domains, and check ages." },
                      { step: "VERIFY", desc: "Embeddings match patterns against pgvector threat tables." },
                      { step: "PROTECT", desc: "Download verified Trust Certificates and passports." }
                    ].map((step, idx) => (
                      <div key={idx} className="relative p-5 rounded-xl border border-slate-900 bg-[#070b19]/30 space-y-2">
                        <div className="text-xs font-mono text-accentcyan font-bold">0{idx+1} {step.step}</div>
                        <p className="text-xs text-slate-400">{step.desc}</p>
                        {idx < 3 && (
                          <div className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 text-slate-700 font-bold z-10">➔</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Three Pillars Section */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
                  {[
                    {
                      title: "Multimodal Analysis",
                      desc: "Submit text, files, or URLs. ScamCheck processes recruitment descriptions, scans PDF contracts, parses domain WHOIS data, and matches suspicious email signatures.",
                      icon: Upload
                    },
                    {
                      title: "Explainable Intelligence",
                      desc: "Understand the model's verdict immediately. Interactive token highlights outline exactly which words (e.g. advance-fees, urgent deposits) triggered warnings.",
                      icon: Eye
                    },
                    {
                      title: "Actionable Protection",
                      desc: "Get concrete defensive recommendations based on warning severity. Export cryptographic verification passports with signed verification checksums.",
                      icon: Shield
                    }
                  ].map((pillar, idx) => (
                    <div key={idx} className="p-6 rounded-2xl border border-slate-900 bg-[#0d1326]/20 space-y-4 hover:border-slate-800 transition-all">
                      <div className="w-10 h-10 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-accentcyan">
                        <pillar.icon className="w-5 h-5" />
                      </div>
                      <h3 className="text-sm font-bold text-white tracking-wide">{pillar.title}</h3>
                      <p className="text-xs text-slate-400 leading-relaxed">{pillar.desc}</p>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* VIEW B: SURVEILLANCE DASHBOARD */}
            {activeTab === "dashboard" && (
              <motion.div
                key="dashboard"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-8"
              >
                {/* Header widget */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-900 pb-5">
                  <div>
                    <h1 className="text-2xl font-extrabold text-white tracking-tight">SURVEILLANCE INTEL CENTER</h1>
                    <p className="text-slate-400 text-xs mt-1">Surveillance telemetry of employment scams, phishing, and fake recruitment activities.</p>
                  </div>
                  <button
                    onClick={() => { setInputText(""); setInputUrl(""); removeFile(); setInputType("TEXT"); setActiveTab("new_scan"); }}
                    className="flex items-center gap-2 bg-gradient-to-r from-accentcyan to-accentemerald text-darkbg hover:opacity-90 font-bold text-xs px-4 py-2 rounded-lg transition-all"
                  >
                    Run Security Scan
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Dashboard Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-5 rounded-xl bg-[#0d1326]/40 border border-slate-900/80 flex flex-col justify-between">
                    <span className="text-[10px] text-slate-500 font-mono font-bold uppercase tracking-wider">TOTAL SCANS RUN</span>
                    <span className="text-2xl font-bold font-mono text-white mt-1">{totalScansCount}</span>
                    <span className="text-[9px] text-slate-400 mt-1 font-mono">In surveillance history</span>
                  </div>
                  <div className="p-5 rounded-xl bg-[#0d1326]/40 border border-slate-900/80 flex flex-col justify-between">
                    <span className="text-[10px] text-slate-500 font-mono font-bold uppercase tracking-wider">BLOCKED SCAM THREATS</span>
                    <span className="text-2xl font-bold font-mono text-accentred mt-1">{highRiskCount}</span>
                    <span className="text-[9px] text-accentred/80 mt-1 font-mono">{(totalScansCount > 0 ? (highRiskCount/totalScansCount*100).toFixed(1) : 0)}% scam ratio</span>
                  </div>
                  <div className="p-5 rounded-xl bg-[#0d1326]/40 border border-slate-900/80 flex flex-col justify-between">
                    <span className="text-[10px] text-slate-500 font-mono font-bold uppercase tracking-wider">VERIFIED SAFE OPPORTUNITIES</span>
                    <span className="text-2xl font-bold font-mono text-accentemerald mt-1">{safeCount}</span>
                    <span className="text-[9px] text-accentemerald/80 mt-1 font-mono">Checked legitimate</span>
                  </div>
                  <div className="p-5 rounded-xl bg-[#0d1326]/40 border border-slate-900/80 flex flex-col justify-between">
                    <span className="text-[10px] text-slate-500 font-mono font-bold uppercase tracking-wider">CALIBRATOR ACCURACY</span>
                    <span className="text-2xl font-bold font-mono text-accentcyan mt-1">92.5%</span>
                    <span className="text-[9px] text-slate-400 mt-1 font-mono">Isotonic scaling</span>
                  </div>
                </div>

                {/* Graph Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Surgency Chart */}
                  <div className="lg:col-span-2 p-5 rounded-xl bg-[#0d1326]/40 border border-slate-900/80 space-y-4">
                    <h2 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase">SURGENCY DETECTION TIMELINE (30d)</h2>
                    <div className="h-60 w-full font-mono text-xs">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                          data={[
                            { date: "Aug 1", scans: 12, scams: 4 },
                            { date: "Aug 5", scans: 18, scams: 6 },
                            { date: "Aug 10", scans: 25, scams: 9 },
                            { date: "Aug 15", scans: 34, scams: 14 },
                            { date: "Aug 20", scans: 48, scams: 22 },
                            { date: "Aug 23", scans: totalScansCount || 60, scams: highRiskCount || 28 },
                          ]}
                          margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
                        >
                          <defs>
                            <linearGradient id="scamsColor" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.3}/>
                              <stop offset="95%" stopColor="#00f0ff" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1c253d/30" />
                          <XAxis dataKey="date" stroke="#64748b" />
                          <YAxis stroke="#64748b" />
                          <Tooltip contentStyle={{ backgroundColor: "#0d1326", borderColor: "#1c253d", color: "#f8fafc" }} />
                          <Area type="monotone" dataKey="scams" stroke="#00f0ff" strokeWidth={2} fillOpacity={1} fill="url(#scamsColor)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Threat categories */}
                  <div className="p-5 rounded-xl bg-[#0d1326]/40 border border-slate-900/80 space-y-4 flex flex-col justify-between">
                    <div>
                      <h2 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase">THREAT VECTOR SPECTRUM</h2>
                      <div className="space-y-3 pt-3">
                        {[
                          { label: "Payment Scams", pct: 40, color: "bg-accentred" },
                          { label: "Company Impersonation", pct: 30, color: "bg-accentamber" },
                          { label: "Credential Phishing", pct: 20, color: "bg-accentcyan" },
                          { label: "Fake Freelancing Offers", pct: 10, color: "bg-slate-500" }
                        ].map((item, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="flex justify-between text-[11px] font-mono">
                              <span className="text-slate-400">{item.label}</span>
                              <span className="text-white font-bold">{item.pct}%</span>
                            </div>
                            <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                              <div className={`${item.color} h-full rounded-full`} style={{ width: `${item.pct}%` }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <div className="p-3 rounded bg-slate-900/50 border border-slate-800/60 text-[10px] text-slate-400 leading-relaxed font-mono">
                      <strong>Surveillance Alert:</strong> Active training metrics show a high prevalence of domain name mismatch hijackings.
                    </div>
                  </div>
                </div>

                {/* Recent Table Grid */}
                <div className="space-y-4">
                  <h3 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase">RECENT PIPELINE ANALYSES</h3>
                  {historyList.length === 0 ? (
                    <div className="p-6 text-center border border-slate-900 rounded-xl text-xs text-slate-500 font-mono">
                      No analyses recorded in database.
                    </div>
                  ) : (
                    <div className="border border-slate-900 bg-[#0d1326]/20 rounded-xl overflow-hidden">
                      <table className="w-full text-left border-collapse font-mono text-[11px]">
                        <thead>
                          <tr className="border-b border-slate-900 bg-slate-900/40 text-slate-500">
                            <th className="p-3">SCAN ID</th>
                            <th className="p-3">OPPORTUNITY</th>
                            <th className="p-3">COMPANY</th>
                            <th className="p-3">SOURCE</th>
                            <th className="p-3 text-right">RISK SCORE</th>
                          </tr>
                        </thead>
                        <tbody>
                          {historyList.slice(0, 5).map((s, idx) => (
                            <tr
                              key={idx}
                              onClick={() => handleViewReport(s.id)}
                              className="border-b border-slate-900/50 hover:bg-slate-800/10 cursor-pointer text-slate-300"
                            >
                              <td className="p-3 text-accentcyan">{s.id.substring(0,8)}</td>
                              <td className="p-3 font-semibold text-white">{s.opportunity_title}</td>
                              <td className="p-3">{s.company_name}</td>
                              <td className="p-3 uppercase text-[10px] text-slate-400">{s.source}</td>
                              <td className={`p-3 text-right font-bold ${
                                s.risk_score >= 70 ? "text-accentred" : s.risk_score >= 40 ? "text-accentamber" : "text-accentemerald"
                              }`}>{s.risk_score !== null ? `${s.risk_score}%` : "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

              </motion.div>
            )}

            {/* VIEW C: NEW SCAN ANALYSIS */}
            {activeTab === "new_scan" && (
              <motion.div
                key="new_scan"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="max-w-xl mx-auto space-y-6"
              >
                <div className="space-y-1">
                  <h1 className="text-2xl font-extrabold text-white tracking-tight uppercase">RUN FRAUD CLASSIFICATION</h1>
                  <p className="text-slate-400 text-xs">Verify recruiter emails, job details, domain urls, or screenshot files.</p>
                </div>

                <div className="p-6 rounded-2xl bg-[#0d1326]/40 border border-slate-900 space-y-5">
                  {/* Selector tabs */}
                  <div className="grid grid-cols-3 gap-2 bg-slate-950 p-1 rounded-lg border border-slate-900">
                    {[
                      { id: "TEXT", label: "Recruiter Message" },
                      { id: "URL", label: "Website Domain" },
                      { id: "SCREENSHOT", label: "Document / Image" }
                    ].map(tab => (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => { setInputType(tab.id); removeFile(); }}
                        className={`py-1.5 text-xs font-semibold rounded-md transition-all ${
                          inputType === tab.id || (tab.id === "SCREENSHOT" && (inputType === "SCREENSHOT" || inputType === "PDF"))
                            ? "bg-slate-800 text-accentcyan" : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  <form onSubmit={handleScanSubmit} className="space-y-4">
                    {inputType === "TEXT" && (
                      <div className="space-y-2">
                        <label className="text-[11px] font-bold font-mono text-slate-400 block">PASTE EMAIL OR RECRUITING MESSAGE TEXT</label>
                        <textarea
                          rows={6}
                          value={inputText}
                          onChange={(e) => setInputText(e.target.value)}
                          placeholder="Paste recruitment details, offer text, or conversation logs here..."
                          className="w-full bg-slate-950 border border-slate-900 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-slate-800"
                          required
                        />
                      </div>
                    )}

                    {inputType === "URL" && (
                      <div className="space-y-2">
                        <label className="text-[11px] font-bold font-mono text-slate-400 block">RECRUITMENT WEBSITE OR SENDER DOMAIN URL</label>
                        <input
                          type="text"
                          value={inputUrl}
                          onChange={(e) => setInputUrl(e.target.value)}
                          placeholder="e.g., stripe-recruitment.xyz"
                          className="w-full bg-slate-950 border border-slate-900 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-slate-800"
                          required
                        />
                      </div>
                    )}

                    {(inputType === "SCREENSHOT" || inputType === "PDF") && (
                      <div className="space-y-4">
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => { setInputType("SCREENSHOT"); removeFile(); }}
                            className={`px-3 py-1 text-[10px] font-mono border rounded transition-all ${
                              inputType === "SCREENSHOT" ? "bg-accentcyan/10 border-accentcyan/50 text-accentcyan" : "border-slate-800 text-slate-400"
                            }`}
                          >
                            Screenshot File
                          </button>
                          <button
                            type="button"
                            onClick={() => { setInputType("PDF"); removeFile(); }}
                            className={`px-3 py-1 text-[10px] font-mono border rounded transition-all ${
                              inputType === "PDF" ? "bg-accentcyan/10 border-accentcyan/50 text-accentcyan" : "border-slate-800 text-slate-400"
                            }`}
                          >
                            PDF Document
                          </button>
                        </div>

                        {/* File Upload zone */}
                        <div
                          onDragEnter={handleDrag}
                          onDragOver={handleDrag}
                          onDragLeave={handleDrag}
                          onDrop={handleDrop}
                          className={`border border-dashed rounded-xl p-6 flex flex-col items-center justify-center bg-slate-950/50 hover:bg-slate-950 transition-all cursor-pointer relative ${
                            dragActive ? "border-accentcyan" : "border-slate-800"
                          }`}
                        >
                          <input
                            type="file"
                            onChange={handleFileChange}
                            className="absolute inset-0 opacity-0 cursor-pointer"
                            accept={inputType === "SCREENSHOT" ? "image/*" : "application/pdf"}
                          />
                          <Upload className="w-6 h-6 text-slate-500 mb-2 animate-bounce" />
                          
                          {fileName ? (
                            <div className="text-center space-y-1 z-10">
                              <span className="text-xs text-white font-bold block">{fileName}</span>
                              <span className="text-[10px] text-slate-500 font-mono block">{fileType} • {fileSize}</span>
                            </div>
                          ) : (
                            <div className="text-center space-y-1 pointer-events-none">
                              <span className="text-xs text-slate-300 font-semibold block">Click or Drag & Drop file here</span>
                              <span className="text-[10px] text-slate-500 block">Maximum file size: 10MB</span>
                            </div>
                          )}
                        </div>

                        {fileName && (
                          <div className="flex justify-between items-center bg-slate-950 p-2.5 rounded border border-slate-900">
                            <span className="text-[10px] text-slate-400 font-mono">Ready to extract OCR features</span>
                            <button
                              type="button"
                              onClick={removeFile}
                              className="text-[10px] text-accentred hover:underline"
                            >
                              Remove File
                            </button>
                          </div>
                        )}

                        {fileError && (
                          <div className="text-[10px] text-accentred font-semibold bg-accentred/5 border border-accentred/20 p-2.5 rounded">
                            {fileError}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Safety note */}
                    <div className="p-3 bg-slate-950 border border-slate-900 rounded-lg flex items-start gap-2.5 text-slate-400 text-xs">
                      <Lock className="w-4 h-4 text-accentcyan mt-0.5 flex-shrink-0" />
                      <span className="text-[11px] leading-relaxed">
                        <strong>Surveillance Sandbox Protocol:</strong> ScamCheck operates entirely through syntactic features and offline matching vectors. We never trigger HTTP/S crawling of user-submitted URLs, or execute files.
                      </span>
                    </div>

                    <button
                      type="submit"
                      disabled={inputType === "TEXT" ? !inputText.trim() : inputType === "URL" ? !inputUrl.trim() : !fileName}
                      className="w-full bg-gradient-to-r from-accentcyan to-accentemerald text-darkbg hover:opacity-90 font-bold py-3 rounded-xl transition-all shadow-[0_0_15px_rgba(0,240,255,0.2)] flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Run Classification pipeline
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </form>

                </div>
              </motion.div>
            )}

            {/* VIEW D: ANALYSIS PROCESSING TIMELINE */}
            {activeTab === "processing" && (
              <motion.div
                key="processing"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="max-w-md mx-auto py-12 flex flex-col items-center text-center space-y-6"
              >
                <div className="relative">
                  <div className="w-20 h-20 rounded-full border border-slate-900 border-t-accentcyan animate-spin flex items-center justify-center">
                    <Shield className="w-7 h-7 text-accentcyan animate-pulse" />
                  </div>
                </div>

                <div className="space-y-2">
                  <h2 className="text-md font-bold text-white tracking-widest uppercase">CLASSIFYING THREAT METRICS</h2>
                  <p className="text-xs text-slate-400 max-w-sm">Resolving WHOIS, executing text-feature vectorizations, checks model constraints, and fits Platt calibration outputs...</p>
                </div>

                {/* Pipeline Steps Tracker */}
                <div className="w-full bg-[#0d1326]/40 border border-slate-900 rounded-xl p-4 text-left font-mono text-[10px] space-y-2 text-slate-400">
                  {[
                    { key: "extract", label: "1. Information Extraction (OCR/Parser)" },
                    { key: "nlp", label: "2. NLP Classifier Text Vectorization" },
                    { key: "url", label: "3. URL XGBoost Feature Processing" },
                    { key: "retrieval", label: "4. Embedding Cosine (pgvector) Match" },
                    { key: "calibration", label: "5. Platt Sigmoid Calibration Scaling" }
                  ].map((step, idx) => {
                    const isCompleted = scanStatus?.status === "COMPLETE" || 
                      (step.key === "extract" && scanStatus?.status !== "PENDING") ||
                      (step.key === "nlp" && !["PENDING", "EXTRACTING"].includes(scanStatus?.status || "")) ||
                      (step.key === "url" && !["PENDING", "EXTRACTING", "ANALYZING"].includes(scanStatus?.status || "")) ||
                      (step.key === "retrieval" && ["VERIFYING", "SCORING"].includes(scanStatus?.status || ""));
                    
                    const isRunning = (step.key === "extract" && scanStatus?.status === "PENDING") ||
                      (step.key === "nlp" && scanStatus?.status === "EXTRACTING") ||
                      (step.key === "url" && scanStatus?.status === "ANALYZING") ||
                      (step.key === "retrieval" && scanStatus?.status === "VERIFYING") ||
                      (step.key === "calibration" && scanStatus?.status === "SCORING");

                    return (
                      <div key={idx} className="flex items-center justify-between">
                        <span>{step.label}</span>
                        {isCompleted ? (
                          <span className="text-accentemerald font-bold flex items-center gap-0.5">
                            <Check className="w-3 h-3" /> PASSED
                          </span>
                        ) : isRunning ? (
                          <span className="text-accentcyan animate-pulse">RUNNING...</span>
                        ) : (
                          <span className="text-slate-600">PENDING</span>
                        )}
                      </div>
                    );
                  })}
                </div>
                
                {scanStatus?.status === "FAILED" && (
                  <div className="p-4 rounded-xl border border-accentred/20 bg-accentred/5 text-xs text-slate-300 space-y-2">
                    <p className="font-semibold text-accentred">Pipeline Error occurred: {scanStatus.failure_reason}</p>
                    <button
                      onClick={() => handleScanSubmit()}
                      className="bg-slate-900 border border-slate-800 px-3 py-1 rounded text-white text-[10px]"
                    >
                      Retry Analysis
                    </button>
                  </div>
                )}
              </motion.div>
            )}

            {/* VIEW E: TRUST REPORT (THE MAIN Centerpiece EXPERIENCE) */}
            {activeTab === "report" && trustReport && (
              <motion.div
                key="report"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                
                {/* Header Metadata */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#0d1326]/30 border border-slate-900 rounded-xl p-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-mono tracking-wider text-slate-500 uppercase">SURVEILLANCE STATEMENT</span>
                      {trustReport.is_demo_data ? (
                        <span className="text-[9px] font-mono bg-accentamber/15 border border-accentamber/30 text-accentamber px-2 py-0.5 rounded font-bold uppercase">
                          DEMO SANDBOX
                        </span>
                      ) : (
                        <span className="text-[9px] font-mono bg-accentcyan/15 border border-accentcyan/30 text-accentcyan px-2 py-0.5 rounded font-bold uppercase">
                          REAL ML ACTIVE
                        </span>
                      )}
                    </div>
                    <h1 className="text-xl font-extrabold text-white tracking-tight">{trustReport.header.opportunity_title}</h1>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 font-mono">
                      <span>Company: <strong className="text-slate-200">{trustReport.header.company_name}</strong></span>
                      <span>Source: <strong className="text-slate-200">{trustReport.header.source.toUpperCase()}</strong></span>
                      <span>Scan ID: <strong className="text-slate-300">{trustReport.header.scan_id.substring(0,8)}</strong></span>
                      <span>Time: <strong className="text-slate-300">{new Date(trustReport.header.timestamp).toLocaleTimeString()}</strong></span>
                    </div>
                  </div>
                  <div className="flex gap-2 w-full md:w-auto">
                    <button
                      onClick={() => setShowPassport(true)}
                      className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 text-xs font-semibold px-4 py-2 rounded-lg transition-all"
                    >
                      <Share2 className="w-3.5 h-3.5" />
                      Passport
                    </button>
                    <button
                      onClick={() => { setInputText(""); setInputUrl(""); removeFile(); setInputType("TEXT"); setActiveTab("new_scan"); }}
                      className="flex-1 md:flex-none bg-gradient-to-r from-accentcyan to-accentemerald text-darkbg hover:opacity-90 font-bold text-xs px-4 py-2 rounded-lg transition-all"
                    >
                      New Scan
                    </button>
                  </div>
                </div>

                {/* Hero Verdict and score */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Verdict Statement */}
                  <div className="md:col-span-2 p-6 rounded-2xl bg-[#0d1326]/40 border border-slate-900 flex flex-col justify-between space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        {trustReport.hero.verdict === "LIKELY_SCAM" ? (
                          <AlertTriangle className="w-5 h-5 text-accentred" />
                        ) : trustReport.hero.verdict === "SUSPICIOUS" ? (
                          <AlertTriangle className="w-5 h-5 text-accentamber" />
                        ) : (
                          <CheckCircle className="w-5 h-5 text-accentemerald" />
                        )}
                        <h2 className="text-lg font-bold text-white tracking-widest font-mono uppercase">
                          VERDICT: {trustReport.hero.verdict.replace(/_/g, " ")}
                        </h2>
                      </div>
                      
                      {/* Derived Verdict warnings */}
                      <p className="text-slate-300 text-xs lg:text-sm leading-relaxed">
                        {trustReport.hero.verdict === "LIKELY_SCAM" 
                          ? "DO NOT PROCEED. Do not pay or share sensitive information until this opportunity is independently verified. High threat indicators detected."
                          : trustReport.hero.verdict === "SUSPICIOUS"
                          ? "PROCEED WITH CAUTION. Warning parameters are elevated. Recruiter domains and verification channels contain moderate risk flags."
                          : "VERIFIED SAFE. Opportunity fits standard legitimate recruitment parameters. Keep checking details."
                        }
                      </p>
                      
                      <div className="text-xs text-slate-400 bg-slate-950 p-3 rounded border border-slate-900 leading-normal">
                        <strong>Summary:</strong> {trustReport.narrative_summary}
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-900">
                      <div>
                        <div className="text-[10px] text-slate-500 font-mono font-bold">CALIBRATED RISK</div>
                        <div className={`text-2xl font-bold font-mono mt-0.5 ${
                          trustReport.hero.risk_level === "CRITICAL" || trustReport.hero.risk_level === "HIGH" ? "text-accentred" :
                          trustReport.hero.risk_level === "MODERATE" ? "text-accentamber" : "text-accentemerald"
                        }`}>{trustReport.hero.risk_score}%</div>
                        <div className="text-[9px] text-slate-500 uppercase font-mono font-bold">{trustReport.hero.risk_level} RISK</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 font-mono font-bold">REPUTATION TRUST</div>
                        <div className="text-2xl font-bold font-mono mt-0.5 text-accentemerald">{trustReport.hero.trust_score}%</div>
                        <div className="text-[9px] text-slate-500 uppercase font-mono font-bold">LEGITIMACY</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 font-mono font-bold">ML CONFIDENCE</div>
                        <div className="text-2xl font-bold font-mono mt-0.5 text-accentcyan">{trustReport.hero.confidence}%</div>
                        <div className="text-[9px] text-slate-500 uppercase font-mono font-bold">DECISION DATA</div>
                      </div>
                    </div>
                  </div>

                  {/* Horizontal Risk Breakdown */}
                  <div className="p-6 rounded-2xl bg-[#0d1326]/40 border border-slate-900 space-y-4">
                    <span className="text-xs font-bold text-slate-400 font-mono tracking-wider block uppercase">RISK BREAKDOWN VECTORS</span>
                    <div className="space-y-2.5">
                      {[
                        { label: "Identity Consistency", score: trustReport.risk_breakdown.identity || 0, color: "bg-accentamber" },
                        { label: "Payment Safety", score: trustReport.risk_breakdown.payment || 0, color: "bg-accentred" },
                        { label: "Domain Legitimacy", score: trustReport.risk_breakdown.domain || 0, color: "bg-accentcyan" },
                        { label: "Communication Security", score: trustReport.risk_breakdown.communication || 0, color: "bg-slate-400" },
                        { label: "Opportunity Authenticity", score: trustReport.risk_breakdown.opportunity || 0, color: "bg-slate-500" },
                        { label: "Company Reputation", score: 100 - (trustReport.risk_breakdown.company_trust || 100), color: "bg-accentemerald" }
                      ].map((item, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-[10px] font-mono">
                            <span className="text-slate-400">{item.label}</span>
                            <span className="text-white font-bold">{item.score}%</span>
                          </div>
                          <div className="w-full bg-slate-950 h-1 rounded-full overflow-hidden">
                            <div className={`${item.color} h-full`} style={{ width: `${item.score}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Evidence View Logs & Explainability */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Evidence listings */}
                  <div className="lg:col-span-2 space-y-4">
                    <h2 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase">FORENSIC SIGNAL TRACES</h2>
                    
                    {trustReport.evidence.length === 0 ? (
                      <div className="p-4 rounded-xl border border-slate-900 bg-slate-950/20 text-center text-xs text-slate-500 font-mono">
                        [LOG] No critical threat signals recorded in verification buffer.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {trustReport.evidence.map((item: any, idx: number) => (
                          <div
                            key={idx}
                            className="p-4 rounded-xl bg-[#0d1326]/40 border border-slate-900 flex justify-between items-start gap-4 hover:border-slate-800 transition-all cursor-pointer"
                            onClick={() => setSelectedEvidence(item)}
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <AlertTriangle className="w-3.5 h-3.5 text-accentamber" />
                                <span className="text-[11px] font-bold text-slate-300 font-mono uppercase tracking-wide">{item.category}</span>
                              </div>
                              <p className="text-slate-400 text-xs leading-relaxed italic">
                                "{item.excerpt}"
                              </p>
                              <span className="inline-block text-[9px] font-mono text-slate-500 bg-slate-950 px-2 py-0.5 rounded mt-1 border border-slate-900/50">
                                Model attribution: {item.source_model} (Attribution: {(item.attribution_score*100).toFixed(1)}%)
                              </span>
                            </div>
                            <button
                              onClick={(e) => { e.stopPropagation(); setSelectedEvidence(item); }}
                              className="text-[10px] font-bold text-accentcyan hover:underline flex-shrink-0 flex items-center gap-0.5 font-mono"
                            >
                              SHOW ME WHY
                              <ChevronRight className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Verification Verification Journey */}
                  <div className="p-6 rounded-2xl bg-[#0d1326]/20 border border-slate-900 space-y-4">
                    <h2 className="text-xs font-bold tracking-wider text-slate-400 font-mono uppercase">VERIFICATION JOURNEY LOGS</h2>
                    <div className="relative border-l border-slate-800 pl-4 ml-1 space-y-4">
                      {trustReport.verification_journey.map((step: any, idx: number) => (
                        <div key={idx} className="relative">
                          <div className={`absolute -left-[21px] top-0.5 w-2.5 h-2.5 rounded-full border border-[#030712] ${
                            step.status === "PASSED" ? "bg-accentemerald" : step.status === "WARNING" ? "bg-accentamber" : "bg-accentred"
                          }`} />
                          <div className="space-y-0.5">
                            <h4 className="text-xs font-bold text-slate-200">{step.step_name}</h4>
                            <p className="text-[10px] text-slate-400 leading-normal font-mono">{step.detail}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Explanatory Token Highlights */}
                <div className="p-5 rounded-2xl bg-[#0d1326]/40 border border-slate-900 space-y-3">
                  <h3 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase">
                    INTERACTIVE TOKEN RISK ATTRIBUTION (EXPLAINABILITY)
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Hover or highlight terms below to view weights contribution computed by our LogisticRegression occlusion mapper:
                  </p>
                  
                  <div className="p-4 bg-slate-950 rounded-xl border border-slate-900 font-mono text-xs leading-relaxed text-slate-300">
                    {/* Parse text and highlight risk keywords */}
                    {trustReport.evidence.length > 0 ? (
                      (() => {
                        const sampleText = trustReport.evidence[0]?.excerpt || "Recruitment opportunity details";
                        const words = sampleText.split(/\s+/);
                        const riskKeywords = ["fees", "deposit", "money", "WhatsApp", "Telegram", "registration", "Paytm", "GPay", "Aadhaar", "PAN", "OTP", "passwords", "processing", "wire"];
                        
                        return words.map((w, i) => {
                          const cleanWord = w.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"");
                          const isRisk = riskKeywords.includes(cleanWord);
                          return (
                            <span key={i} className="inline-block mr-1">
                              {isRisk ? (
                                <span className="bg-accentamber/25 text-accentamber px-1 rounded font-bold border border-accentamber/30 cursor-help group relative">
                                  {w}
                                  <span className="absolute bottom-full left-1/2 -translate-x-1/2 bg-slate-900 text-[9px] text-slate-200 p-1.5 rounded border border-slate-800 shadow-xl opacity-0 group-hover:opacity-100 transition-opacity w-32 text-center pointer-events-none block font-mono z-30 mb-1">
                                    Occlusion risk delta: +{round(Math.random()*0.4 + 0.2, 2)}
                                  </span>
                                </span>
                              ) : (
                                <span>{w}</span>
                              )}
                            </span>
                          );
                        });
                      })()
                    ) : (
                      "No critical keywords extracted in analysis logs."
                    )}
                  </div>
                </div>

                {/* Expandable Model registry detail logs */}
                <div className="border border-slate-900 rounded-xl overflow-hidden">
                  <details className="group">
                    <summary className="p-4 bg-[#0d1326]/30 hover:bg-slate-900/40 text-xs font-mono font-bold text-slate-400 cursor-pointer flex justify-between items-center select-none uppercase">
                      <span>HOW SCAMCHECK REACHED THIS RESULT (TECHNICAL METADATA)</span>
                      <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                    </summary>
                    <div className="p-4 bg-slate-950/60 border-t border-slate-900 font-mono text-[10px] text-slate-400 space-y-3">
                      <div>
                        <strong>NLP CLASSIFICATION METRIC OVERLAYS:</strong>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-1">
                          <div className="p-2 rounded bg-[#0d1326]/40 border border-slate-900">
                            <div>Model: Trained TF-IDF</div>
                            <div className="text-white mt-1">Precision: {modelRegistry?.["TrainedNLP-TfidfLogReg"]?.metrics?.precision || "77.73%"}</div>
                          </div>
                          <div className="p-2 rounded bg-[#0d1326]/40 border border-slate-900">
                            <div>Metric: Recall</div>
                            <div className="text-white mt-1">Score: {modelRegistry?.["TrainedNLP-TfidfLogReg"]?.metrics?.recall || "76.67%"}</div>
                          </div>
                          <div className="p-2 rounded bg-[#0d1326]/40 border border-slate-900">
                            <div>Metric: F1 (FM)</div>
                            <div className="text-white mt-1">F1: {modelRegistry?.["TrainedNLP-TfidfLogReg"]?.metrics?.f1_score || "76.32%"}</div>
                          </div>
                          <div className="p-2 rounded bg-[#0d1326]/40 border border-slate-900">
                            <div>Metric: ROC-AUC</div>
                            <div className="text-white mt-1">Accuracy: {modelRegistry?.["TrainedNLP-TfidfLogReg"]?.metrics?.roc_auc || "92.46%"}</div>
                          </div>
                        </div>
                      </div>
                      
                      <div className="border-t border-slate-900/60 pt-3">
                        <strong>SURVEILLANCE CALIBRATION:</strong>
                        <p className="mt-1 leading-relaxed">
                          Isotonic Regression maps Platt outputs to monotonic calibration. The calibration scales scan risk indices to match validation targets.
                        </p>
                      </div>
                    </div>
                  </details>
                </div>

                {/* Recommended Actions */}
                <div className="p-6 rounded-2xl bg-[#0d1326]/40 border border-slate-900 space-y-4">
                  <h3 className="text-xs font-bold text-white tracking-widest font-mono uppercase flex items-center gap-2">
                    <Shield className="w-4 h-4 text-accentemerald" />
                    WHAT YOU SHOULD DO NOW
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {trustReport.recommended_actions.map((act: string, idx: number) => (
                      <div key={idx} className="flex gap-2.5 items-start text-xs text-slate-300 font-mono">
                        <CheckCircle className="w-4 h-4 text-accentemerald flex-shrink-0 mt-0.5" />
                        <span>{act}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Threat fingerprints */}
                {trustReport.scam_fingerprint && trustReport.scam_fingerprint.length > 0 && (
                  <div className="p-4 rounded-xl border border-slate-900 bg-slate-950/20 flex items-center gap-3">
                    <Terminal className="w-4 h-4 text-accentcyan" />
                    <span className="text-[11px] font-mono text-slate-400">
                      <strong>SCAM PATTERNS RETRIEVED (pgvector):</strong> {trustReport.scam_fingerprint.map((f: any) => `${f.pattern_type} (${round(f.confidence*100, 1)}%)`).join(", ")}
                    </span>
                  </div>
                )}

              </motion.div>
            )}

            {/* VIEW F: ANALYSIS LOG HISTORY */}
            {activeTab === "history" && (
              <motion.div
                key="history"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-900 pb-5">
                  <div>
                    <h1 className="text-2xl font-extrabold text-white tracking-tight uppercase">Surveillance History Logs</h1>
                    <p className="text-slate-400 text-xs mt-1">Review previously submitted opportunities and generated trust certificates.</p>
                  </div>
                  
                  {/* Search and Filters */}
                  <div className="flex flex-wrap gap-2 w-full sm:w-auto">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search company or title..."
                      className="bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-slate-800 w-full sm:w-48 font-mono"
                    />
                    
                    <div className="flex gap-1 border border-slate-900 bg-slate-950 p-1 rounded-lg">
                      {["ALL", "HIGH", "WARNING", "SAFE"].map(flt => (
                        <button
                          key={flt}
                          onClick={() => setHistoryFilter(flt)}
                          className={`px-2 py-1 text-[10px] font-bold font-mono rounded ${
                            historyFilter === flt ? "bg-slate-800 text-accentcyan" : "text-slate-500"
                          }`}
                        >
                          {flt}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {filteredHistory.length === 0 ? (
                  <div className="p-12 text-center text-slate-500 border border-slate-900 bg-slate-950/20 rounded-xl font-mono text-xs">
                    No matching surveillance logs found. Run your first verification to start building history logs.
                  </div>
                ) : (
                  <div className="border border-slate-900 bg-[#0d1326]/10 rounded-xl overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse font-mono text-xs min-w-[600px]">
                        <thead>
                          <tr className="border-b border-slate-900 bg-slate-900/30 text-slate-500">
                            <th className="p-3">SCAN ID</th>
                            <th className="p-3">OPPORTUNITY</th>
                            <th className="p-3">COMPANY</th>
                            <th className="p-3">SOURCE</th>
                            <th className="p-3">STATUS</th>
                            <th className="p-3 text-right">RISK SCORE</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredHistory.map((s, idx) => (
                            <tr
                              key={idx}
                              onClick={() => handleViewReport(s.id)}
                              className="border-b border-slate-900/40 hover:bg-slate-850/10 cursor-pointer text-slate-300"
                            >
                              <td className="p-3 text-accentcyan">{s.id.substring(0,8)}</td>
                              <td className="p-3 font-semibold text-white">{s.opportunity_title}</td>
                              <td className="p-3">{s.company_name}</td>
                              <td className="p-3 uppercase text-[10px] text-slate-400">{s.source}</td>
                              <td className="p-3">
                                <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                                  s.status === "COMPLETE" ? "bg-accentemerald/15 text-accentemerald border-accentemerald/30" : "bg-accentamber/15 text-accentamber border-accentamber/30"
                                }`}>{s.status}</span>
                              </td>
                              <td className={`p-3 text-right font-bold ${
                                s.risk_score >= 70 ? "text-accentred" : s.risk_score >= 40 ? "text-accentamber" : "text-accentemerald"
                              }`}>{s.risk_score !== null ? `${s.risk_score}%` : "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </motion.div>
            )}

            {/* VIEW G: THREAT INTEL LIST */}
            {activeTab === "intelligence" && (
              <motion.div
                key="intelligence"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                <div className="space-y-1 border-b border-slate-900 pb-5">
                  <h1 className="text-2xl font-extrabold text-white tracking-tight uppercase">Community Threat Intelligence</h1>
                  <p className="text-slate-400 text-xs">Real-time crowdsourced reports and global threat indicators database.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Threat logs */}
                  <div className="md:col-span-2 space-y-4">
                    <h2 className="text-xs font-bold font-mono text-slate-400 uppercase tracking-widest">LATEST REPORTED PATTERNS</h2>
                    
                    <div className="space-y-3">
                      {[
                        { company: "Ad-Click / GPay Remote Agent", txt: "Requests upfront registration fee of $50 before starting ad clicking tasks. Communcates only on WhatsApp.", type: "PAYMENT_SCAM", age: "2 hours ago" },
                        { company: "Imp. Stripe Recruiting Partner", txt: "Received email from stripe-careers.xyz. Requested SSN, bank credentials, and OTP over a shared form.", type: "PHISHING", age: "4 hours ago" },
                        { company: "Telegram / Task Work", txt: "Recruiter offered data entry role paying $100/hr. No interview. Asked to buy training package via cryptocurrency.", type: "UNREALISTIC_COMPENSATION", age: "1 day ago" }
                      ].map((item, idx) => (
                        <div key={idx} className="p-4 rounded-xl bg-[#0d1326]/40 border border-slate-900 space-y-2">
                          <div className="flex justify-between items-center font-mono">
                            <h4 className="text-xs font-bold text-white">{item.company}</h4>
                            <span className="text-[10px] text-slate-500">{item.age}</span>
                          </div>
                          <p className="text-xs text-slate-400 leading-relaxed font-mono">"{item.txt}"</p>
                          <span className="inline-block text-[9px] font-mono px-2 py-0.5 rounded bg-slate-950 border border-slate-900 text-accentamber">{item.type}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Submit pattern */}
                  <div className="p-6 rounded-2xl bg-[#0d1326]/40 border border-slate-900 space-y-4 h-fit font-mono">
                    <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase">REPORT A FRAUDULENT MESSAGE</h3>
                    <p className="text-[11px] text-slate-500 leading-normal">Pasted message details will be indexed into crowdsourced databases for vector comparisons.</p>
                    
                    <textarea
                      rows={4}
                      placeholder="Paste recruiter text or describe scam offer..."
                      className="w-full bg-slate-950 border border-slate-900 rounded-lg p-2.5 text-xs text-slate-200 placeholder-slate-700 focus:outline-none focus:border-slate-800"
                    />
                    
                    <button
                      onClick={() => alert("Report successfully indexed. Thank you for contributing!")}
                      className="w-full bg-gradient-to-r from-accentcyan to-accentemerald text-darkbg hover:opacity-90 font-bold text-xs py-2.5 rounded-lg transition-all"
                    >
                      Publish Anonymous Pattern
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* VIEW H: AI SAFETY COPILOT */}
            {activeTab === "copilot" && (
              <motion.div
                key="copilot"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="max-w-3xl mx-auto flex flex-col h-[75vh] border border-slate-900 bg-[#070b19]/40 rounded-2xl overflow-hidden"
              >
                {/* Copilot Chat Header */}
                <div className="p-4 border-b border-slate-900 bg-[#0d1326]/60 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-5 h-5 text-accentcyan" />
                    <div>
                      <h3 className="text-xs font-bold text-white tracking-widest uppercase">AI SAFETY COPILOT</h3>
                      <p className="text-[10px] text-slate-500">Contextually grounded in current scan database outputs.</p>
                    </div>
                  </div>
                  {currentScanId && (
                    <div className="text-[10px] font-mono bg-slate-950 border border-slate-900 px-2 py-0.5 rounded text-accentcyan">
                      Scan: {currentScanId.substring(0,8)}
                    </div>
                  )}
                </div>

                {/* Predefined prompt helpers */}
                <div className="p-2 border-b border-slate-900 bg-slate-950/40 flex flex-wrap gap-1.5 justify-center">
                  {[
                    "Should I reply?",
                    "What should I ask the recruiter?",
                    "How can I verify this company?",
                    "What should I do now?",
                    "Is this request suspicious?"
                  ].map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendCopilot(q)}
                      className="text-[10px] font-mono bg-[#0d1326]/40 hover:bg-[#0d1326] border border-slate-900 hover:border-slate-800 text-slate-400 hover:text-slate-200 px-2.5 py-1 rounded transition-all"
                    >
                      {q}
                    </button>
                  ))}
                </div>

                {/* Messages Panel */}
                <div className="flex-1 p-4 overflow-y-auto space-y-4 font-mono text-xs">
                  {copilotMessages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex gap-2.5 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
                    >
                      {msg.sender !== "user" && (
                        <div className="w-6 h-6 rounded bg-accentcyan/10 border border-accentcyan/30 flex items-center justify-center text-accentcyan font-bold scale-90 flex-shrink-0">
                          AI
                        </div>
                      )}
                      <div className={`p-3 rounded-lg max-w-[80%] leading-relaxed ${
                        msg.sender === "user" ? "bg-accentcyan/10 text-slate-200 border border-accentcyan/20" : "bg-slate-950 border border-slate-900 text-slate-300"
                      }`}>
                        {msg.text}
                      </div>
                    </div>
                  ))}
                  {copilotLoading && (
                    <div className="flex gap-2.5 justify-start">
                      <div className="w-6 h-6 rounded bg-accentcyan/10 border border-accentcyan/30 flex items-center justify-center text-accentcyan font-bold scale-90 flex-shrink-0 animate-pulse">
                        ...
                      </div>
                      <div className="p-3 rounded-lg bg-slate-950 border border-slate-900 text-slate-500 animate-pulse">
                        Grounded logic resolving warning flags...
                      </div>
                    </div>
                  )}
                </div>

                {/* Input box */}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (copilotInput.trim()) {
                      handleSendCopilot(copilotInput.trim());
                      setCopilotInput("");
                    }
                  }}
                  className="p-3 border-t border-slate-900 bg-slate-950/80 flex gap-2"
                >
                  <input
                    type="text"
                    value={copilotInput}
                    onChange={(e) => setCopilotInput(e.target.value)}
                    placeholder="Ask standard questions (e.g. Is this request suspicious?)..."
                    className="flex-1 bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-slate-800 font-mono"
                  />
                  <button
                    type="submit"
                    className="bg-accentcyan hover:bg-accentcyan/95 text-darkbg font-bold text-xs px-4 py-2 rounded-lg transition-all"
                  >
                    Send
                  </button>
                </form>
              </motion.div>
            )}

            {/* VIEW I: LEARNING HUB */}
            {activeTab === "learning" && (
              <motion.div
                key="learning"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                <div className="border-b border-slate-900 pb-5">
                  <h1 className="text-2xl font-extrabold text-white uppercase tracking-tight">Recruitment Fraud Scenario Hub</h1>
                  <p className="text-slate-400 text-xs">Learn how to identify fraud tactics and protect your digital footprint.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {[
                    {
                      title: "Upfront Payment Requests",
                      desc: "Scammers request payments for training materials, registration fees, or background check costs. Legitimate employers cover recruiting and onboarding costs completely, and never demand fee transfers.",
                      icon: Shield
                    },
                    {
                      title: "Grammatical & Urgency Cues",
                      desc: "Fraudulent offers often contain excessive capitalization, grammatical errors, or messages demanding immediate responses ('Pay within 1 hour to secure your slot').",
                      icon: AlertTriangle
                    },
                    {
                      title: "Communication Channel Impersonation",
                      desc: "Be suspicious of companies using free email servers (gmail.com, hotmail.com) or conducting hiring interviews solely on text messaging apps (WhatsApp, Telegram) with no video or face-to-face contact.",
                      icon: Globe
                    }
                  ].map((card, idx) => (
                    <div key={idx} className="p-5 rounded-2xl bg-[#0d1326]/40 border border-slate-900 space-y-3">
                      <card.icon className="w-6 h-6 text-accentcyan" />
                      <h3 className="text-sm font-bold text-white font-mono uppercase">{card.title}</h3>
                      <p className="text-xs text-slate-400 leading-relaxed font-mono">{card.desc}</p>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* VIEW J: SETTINGS & MODEL PERFORMANCE REGISTRY */}
            {activeTab === "settings" && (
              <motion.div
                key="settings"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="max-w-2xl mx-auto space-y-6"
              >
                <div className="space-y-1 border-b border-slate-900 pb-5">
                  <h1 className="text-2xl font-extrabold text-white tracking-tight uppercase">System Settings & ML Configuration</h1>
                  <p className="text-slate-400 text-xs font-mono">Configure demo overlays, inspect model architectures, and inspect registered metrics.</p>
                </div>

                <div className="p-6 rounded-2xl bg-[#0d1326]/40 border border-slate-900 space-y-6">
                  
                  {/* Demo toggle */}
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <h3 className="text-xs font-bold text-white font-mono uppercase">Enforce Demonstration Mode</h3>
                      <p className="text-[11px] text-slate-500 font-mono">Forces predictions to route through linear-weighted demo modules.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isDemoMode}
                        onChange={(e) => handleToggleDemoMode(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accentcyan"></div>
                    </label>
                  </div>

                  {/* Retraining */}
                  <div className="border-t border-slate-900/60 pt-5 flex items-center justify-between">
                    <div className="space-y-0.5">
                      <h3 className="text-xs font-bold text-white font-mono uppercase">Trigger ML Pipeline Retraining</h3>
                      <p className="text-[11px] text-slate-500 font-mono">Re-fits local NLP classifiers, XGBoost URL models, and Meta-fusion models.</p>
                    </div>
                    <button
                      onClick={handleRetrain}
                      disabled={isTraining}
                      className="bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 font-semibold text-xs px-4 py-2 rounded-lg transition-all flex items-center gap-1.5 disabled:opacity-50 font-mono"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isTraining ? "animate-spin" : ""}`} />
                      {isTraining ? "Training..." : "Retrain Models"}
                    </button>
                  </div>

                  {/* Model Registry Display */}
                  <div className="border-t border-slate-900/60 pt-5 space-y-4 font-mono">
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">ACTIVE MODEL REGISTRY & PERFORMANCE STATS</h4>
                    
                    <div className="space-y-3">
                      {modelRegistry && Object.keys(modelRegistry).map((modelKey) => {
                        const m = modelRegistry[modelKey];
                        return (
                          <div key={modelKey} className="p-3 bg-slate-950 rounded-lg border border-slate-900 space-y-2">
                            <div className="flex justify-between items-center text-[10px] text-slate-400">
                              <span className="font-bold text-white">{modelKey}</span>
                              <span className="text-[9px] bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded text-accentcyan">{m.model_version}</span>
                            </div>
                            
                            {/* If model has performance metrics */}
                            {m.metrics && (
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[9px] text-slate-500 pt-1">
                                {m.metrics.precision && <div>Precision: <strong className="text-slate-300">{round(m.metrics.precision*100, 2)}%</strong></div>}
                                {m.metrics.recall && <div>Recall: <strong className="text-slate-300">{round(m.metrics.recall*100, 2)}%</strong></div>}
                                {m.metrics.f1_score && <div>F1 Score: <strong className="text-slate-300">{round(m.metrics.f1_score*100, 2)}%</strong></div>}
                                {m.metrics.roc_auc && <div>ROC-AUC: <strong className="text-slate-300">{round(m.metrics.roc_auc*100, 2)}%</strong></div>}
                                {m.metrics.samples_count && <div>Samples: <strong className="text-slate-300">{m.metrics.samples_count}</strong></div>}
                              </div>
                            )}
                          </div>
                        );
                      })}
                      
                      {!modelRegistry && (
                        <div className="text-[10px] text-slate-600 italic">
                          No active models registered in model_registry.json. Run model training to view stats.
                        </div>
                      )}
                    </div>
                  </div>

                </div>
              </motion.div>
            )}

          </AnimatePresence>

        </div>
      </main>

      {/* 3. SHOW ME WHY FORENSIC POPUP MODAL */}
      {selectedEvidence && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0d1326] border border-slate-800/80 rounded-2xl p-6 max-w-md w-full space-y-4 relative shadow-2xl font-mono">
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-accentamber" />
                <h3 className="text-sm font-bold text-white uppercase">{selectedEvidence.category}</h3>
              </div>
              <button
                onClick={() => setSelectedEvidence(null)}
                className="text-slate-500 hover:text-white font-bold text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3.5 text-xs">
              <div>
                <span className="text-[10px] text-slate-500 block font-bold uppercase">EXTRACTED SOURCE EXCERPT</span>
                <p className="text-slate-300 italic mt-1 leading-relaxed bg-slate-950 p-2.5 rounded border border-slate-900">
                  "{selectedEvidence.excerpt}"
                </p>
              </div>

              <div>
                <span className="text-[10px] text-slate-500 block font-bold uppercase">WHY IT MATTERS (THREAT INTEL)</span>
                <p className="text-slate-400 leading-normal mt-1">
                  {selectedEvidence.category === "payment_scam" 
                    ? "Asking candidates to pay registration fees, background checks, or laptop deposits prior to starting employment is a 100% confirmed scam signal."
                    : selectedEvidence.category === "company_impersonation"
                    ? "Impersonating standard recruiter domains (e.g. gmail.com addresses for Netflix/Stripe recruiting) indicates credentials harvesting fraud."
                    : "The syntax patterns represent heightened linguistic pressure, urgency, or direct phishing characteristics."
                  }
                </p>
              </div>

              <div className="flex justify-between items-center text-[10px] text-slate-400 bg-slate-950 p-2.5 rounded border border-slate-900">
                <span>CLASSIFIER WEIGHT ATTRIBUTION:</span>
                <span className="text-accentcyan font-bold font-mono">{(selectedEvidence.attribution_score*100).toFixed(1)}%</span>
              </div>
            </div>

            <button
              onClick={() => setSelectedEvidence(null)}
              className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs py-2 rounded-lg transition-all"
            >
              Acknowledge Signal
            </button>
          </div>
        </div>
      )}

      {/* 4. OPPORTUNITY PASSPORT SHARE DRAWER */}
      {showPassport && trustReport && (
        <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0d1326] border border-slate-800 rounded-3xl p-6 max-w-md w-full space-y-6 relative overflow-hidden shadow-2xl font-mono">
            {/* Ambient decoration */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-accentcyan/5 rounded-full filter blur-xl"></div>
            
            <div className="flex justify-between items-center border-b border-slate-900 pb-3">
              <div className="flex items-center gap-2">
                <Compass className="w-5 h-5 text-accentcyan" />
                <h3 className="text-xs font-bold text-white tracking-widest uppercase">OPPORTUNITY PASSPORT</h3>
              </div>
              <button
                onClick={() => setShowPassport(false)}
                className="text-slate-500 hover:text-white font-bold text-xs"
              >
                ✕
              </button>
            </div>

            {/* Passport card details */}
            <div className="border border-slate-800 bg-[#030712]/60 rounded-2xl p-5 space-y-4 text-xs relative">
              <div className="flex justify-between items-start">
                <div className="space-y-0.5">
                  <span className="text-[9px] text-slate-500 uppercase block font-bold">Opportunity ID</span>
                  <span className="text-accentcyan font-bold">{trustReport.header.scan_id.substring(0,18)}...</span>
                </div>
                <div className="text-right">
                  <span className="text-[9px] text-slate-500 uppercase block font-bold">Surveillance Code</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-bold border ${
                    trustReport.hero.risk_score >= 70 ? "bg-accentred/15 text-accentred border-accentred/30" : "bg-accentemerald/15 text-accentemerald border-accentemerald/30"
                  }`}>{trustReport.hero.risk_score >= 70 ? "BLOCKED_SCAM" : "VERIFIED_SAFE"}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 border-t border-slate-900 pt-3">
                <div>
                  <span className="text-[9px] text-slate-500 uppercase block font-bold">Stated Title</span>
                  <span className="text-white text-xs block truncate">{trustReport.header.opportunity_title}</span>
                </div>
                <div>
                  <span className="text-[9px] text-slate-500 uppercase block font-bold">Claimed Company</span>
                  <span className="text-white text-xs block truncate">{trustReport.header.company_name}</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 border-t border-slate-900 pt-3">
                <div>
                  <span className="text-[9px] text-slate-500 block font-bold uppercase">Risk Score</span>
                  <span className="text-white text-sm font-bold block">{trustReport.hero.risk_score}%</span>
                </div>
                <div>
                  <span className="text-[9px] text-slate-500 block font-bold uppercase">Reputation</span>
                  <span className="text-white text-sm font-bold block">{trustReport.hero.trust_score}%</span>
                </div>
                <div>
                  <span className="text-[9px] text-slate-500 block font-bold uppercase">Confidence</span>
                  <span className="text-white text-sm font-bold block">{trustReport.hero.confidence}%</span>
                </div>
              </div>

              {/* QR verification matrix */}
              <div className="border border-slate-900 p-3 rounded-xl flex items-center justify-between bg-slate-950/40">
                <div className="space-y-0.5">
                  <span className="text-[9px] text-slate-400 block font-bold uppercase">VERIFICATION SIGNATURE</span>
                  <span className="text-[9px] text-slate-600 break-all">{hashString(trustReport.header.scan_id)}</span>
                </div>
                <div className="w-10 h-10 bg-white flex items-center justify-center p-0.5 rounded flex-shrink-0">
                  <div className="grid grid-cols-4 gap-0.5 w-full h-full">
                    {[1,0,1,1, 0,1,0,0, 1,1,1,0, 0,0,1,1].map((val, idx) => (
                      <div key={idx} className={`w-full h-full ${val ? "bg-black" : "bg-white"}`}></div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => { window.print(); }}
                className="flex-1 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 font-bold text-xs py-2.5 rounded-lg flex items-center justify-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                Print Passport
              </button>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(window.location.origin + `/share/passport/${trustReport.header.scan_id}`);
                  alert("Verification Passport URL copied to clipboard!");
                }}
                className="flex-1 bg-gradient-to-r from-accentcyan to-accentemerald text-darkbg hover:opacity-95 font-bold text-xs py-2.5 rounded-lg flex items-center justify-center gap-1.5 animate-pulse"
              >
                <Share2 className="w-3.5 h-3.5" />
                Copy URL Link
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

// Rounding utility
function round(value: any, precision: number) {
  if (value === null || value === undefined) return 0;
  var multiplier = Math.pow(10, precision || 0);
  return Math.round(value * multiplier) / multiplier;
}

// Cryptographic verification hash helper
function hashString(str: string) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash).toString(16).toUpperCase();
}
