"use client";

import { useState, useRef, useEffect } from "react";
import {
    Send, Bot, Trash2, FileText,
    ChevronDown, ChevronUp, Zap, Brain, LogOut, Upload, Database,
    CheckCircle2, Activity, BookOpen, BarChart2, LayoutDashboard,
    Sparkles, Network, ExternalLink
} from "lucide-react";
import { cn, API_URL } from "@/lib/utils";
import { Message, Session, FileItem, ThinkingStep } from "@/types/chat";
import { motion, AnimatePresence } from "framer-motion";
import Sidebar from "./Sidebar";
import Dashboard from "./Dashboard";
import KnowledgeBase from "./KnowledgeBase";
import Documentation from "./Documentation";
import DataAnalysisView from "./DataAnalysisView";
import ReportBuilderView from "./ReportBuilderView";
import { AuthUser } from "@/lib/useAuth";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChatChart } from "./ChatChart";
import { useChatStream } from "@/hooks/useChatStream";


interface ChatInterfaceProps {
    user: AuthUser;
    onLogout: () => void;
}

type ChatMode = "fast" | "reasoning" | "deep_analytic";

const MODE_CONFIG: Record<ChatMode, { label: string; icon: any; color: string; bg: string; description: string }> = {
    fast: {
        label: "Fast",
        icon: Zap,
        color: "text-emerald-500",
        bg: "bg-emerald-500/10 border-emerald-500/20",
        description: "Quick answers from your knowledge base",
    },

    reasoning: {
        label: "High Reasoning",
        icon: Sparkles,
        color: "text-amber-500",
        bg: "bg-amber-500/10 border-amber-500/20",
        description: "Agentic: Plan → Research → Reflect → Answer",
    },
    deep_analytic: {
        label: "Deep Analytic",
        icon: Network,
        color: "text-cyan-500",
        bg: "bg-cyan-500/10 border-cyan-500/20",
        description: "GraphRAG: Entity & relationship analysis",
    },
};

// ── Thinking Panel (Claude-style) ──────────────────────────────────────────
function ThinkingPanel({ steps, isOpen, onToggle, isComplete }: {
    steps: ThinkingStep[];
    isOpen: boolean;
    onToggle: () => void;
    isComplete: boolean;
}) {
    if (!steps || steps.length === 0) return null;

    const stepColors: Record<string, string> = {
        planning: "text-amber-600 bg-amber-50 border-amber-200",
        reflecting: "text-purple-600 bg-purple-50 border-purple-200",
        generating: "text-blue-600 bg-blue-50 border-blue-200",
        searching: "text-cyan-600 bg-cyan-50 border-cyan-200",
        graph_building: "text-emerald-600 bg-emerald-50 border-emerald-200",
        graph_traversal: "text-teal-600 bg-teal-50 border-teal-200",
    };

    const getStepColor = (step: string) => {
        if (step.startsWith("task_")) return "text-blue-600 bg-blue-50 border-blue-200";
        return stepColors[step] || "text-slate-600 bg-slate-50 border-slate-200";
    };

    const latestStep = steps[steps.length - 1];

    return (
        <div className="mb-3 rounded-xl border border-slate-200 overflow-hidden">
            {/* Header */}
            <button
                onClick={onToggle}
                className="w-full flex items-center gap-2 px-3 py-2 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
            >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                    {!isComplete ? (
                        <div className="flex gap-1 shrink-0">
                            <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                            <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                            <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce" />
                        </div>
                    ) : (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    )}
                    <span className="text-[11px] font-semibold text-slate-600 truncate">
                        {isComplete ? `Reasoning selesai (${steps.length} langkah)` : latestStep?.content?.split("\n")[0] || "Thinking..."}
                    </span>
                </div>
                {isOpen ? <ChevronUp className="w-3.5 h-3.5 text-slate-400 shrink-0" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
            </button>

            {/* Steps */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="px-3 py-2 space-y-2 max-h-64 overflow-y-auto bg-white border-t border-slate-100">
                            {steps.map((s, i) => (
                                <div key={i} className={cn("px-2.5 py-2 rounded-lg border text-[11px] leading-relaxed", getStepColor(s.step))}>
                                    <div className="[&>*]:mb-1 [&>*:last-child]:mb-0 [&_strong]:font-semibold">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {s.content}
                                        </ReactMarkdown>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}


export default function ChatInterface({ user, onLogout }: ChatInterfaceProps) {
    const [mode, setMode] = useState<ChatMode>("fast");
    const [sessions, setSessions] = useState<Session[]>([]);
    const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    const [activeView, setActiveView] = useState<"chat" | "knowledge" | "dashboard" | "documentation" | "data-analysis" | "report-builder">("report-builder");
    const scrollRef = useRef<HTMLDivElement>(null);
    const [input, setInput] = useState("");
    const [useOllama, setUseOllama] = useState<boolean>(false);
    const [isModeMenuOpen, setIsModeMenuOpen] = useState(false);

    const fetchSessions = async () => {
        try {
            const res = await fetch(`${API_URL}/history`, {
                headers: { "Authorization": `Bearer ${user.token}` }
            });
            setSessions(await res.json());
        } catch (e) { console.error(e); }
    };

    const { messages, setMessages, isLoading, setIsLoading, handleSubmit: streamHandleSubmit } = useChatStream({
        user,
        currentSessionId,
        setCurrentSessionId,
        mode,
        selectedFiles,
        fetchSessions,
        useOllama
    });

    const scrollToBottom = () => {
        scrollRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => { fetchSessions(); }, []);
    useEffect(() => { scrollToBottom(); }, [messages]);

    const handleSelectSession = async (id: string) => {
        setIsLoading(true);
        try {
            const res = await fetch(`${API_URL}/history/${id}`, {
                headers: { "Authorization": `Bearer ${user.token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setMessages(data.messages || []);
                setCurrentSessionId(id);
            }
        } catch (e) { console.error(e); }
        finally { setIsLoading(false); }
    };

    const handleNewChat = () => { setMessages([]); setCurrentSessionId(null); setSelectedFiles([]); };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const userInput = input;
        setInput("");
        streamHandleSubmit(userInput);
    };

    const ActiveMode = MODE_CONFIG[mode];

    // Toggle thinking panel for a specific message
    const toggleThinking = (msgIdx: number) => {
        setMessages(prev => {
            const m = [...prev];
            m[msgIdx].thinkingOpen = !m[msgIdx].thinkingOpen;
            return m;
        });
    };


    return (
        <div className="flex h-screen w-full bg-[#f8fafc] text-slate-900 relative font-sans overflow-hidden">
            {/* Background ambience */}
            <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
                <div className="absolute top-[-15%] left-[-5%] w-[45%] h-[45%] bg-sky-200/40 rounded-full blur-[130px]" />
                <div className="absolute bottom-[-15%] right-[-5%] w-[45%] h-[45%] bg-cyan-200/35 rounded-full blur-[130px]" />
                <div className="absolute top-[50%] left-[50%] -translate-x-1/2 -translate-y-1/2 w-[30%] h-[30%] bg-blue-200/20 rounded-full blur-[100px]" />
            </div>

            <Sidebar
                sessions={sessions}
                currentSessionId={currentSessionId}
                onSelectSession={handleSelectSession}
                onNewChat={handleNewChat}
                user={user}
                onLogout={onLogout}
                activeView={activeView}
                onViewChange={setActiveView}
            />

            {/* Main Content */}
            <div className="flex-1 flex flex-col h-full z-10 relative min-w-0">

                {/* Header */}
                <header className="flex items-center justify-between py-4 px-6 shrink-0 h-16 z-20">
                    <div className="flex items-center gap-3">
                        {activeView === "knowledge" ? (
                            <div className="flex items-center gap-2 text-slate-800 font-semibold text-lg">
                                <Database className="w-5 h-5 text-blue-500" />
                                Knowledge Base
                            </div>
                        ) : activeView === "dashboard" ? (
                            <div className="flex items-center gap-2 text-slate-800 font-semibold text-lg">
                                <Activity className="w-5 h-5 text-blue-500" />
                                Dashboard
                            </div>
                        ) : activeView === "documentation" ? (
                            <div className="flex items-center gap-2 text-slate-800 font-semibold text-lg">
                                <BookOpen className="w-5 h-5 text-blue-500" />
                                Documentation
                            </div>
                        ) : activeView === "data-analysis" ? (
                            <div className="flex items-center gap-2 text-slate-800 font-semibold text-lg">
                                <BarChart2 className="w-5 h-5 text-sky-500" />
                                Data Analysis
                            </div>
                        ) : activeView === "report-builder" ? (
                            <div className="flex items-center gap-2 text-slate-800 font-semibold text-lg">
                                <LayoutDashboard className="w-5 h-5 text-blue-500" />
                                Report Builder
                            </div>
                        ) : (
                            <div className={cn("flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border", ActiveMode.bg, ActiveMode.color)}>
                                <ActiveMode.icon className="w-3 h-3" />
                                {ActiveMode.label} mode
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 pr-3 border-r border-slate-200">
                            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-sky-500 to-blue-600 flex items-center justify-center text-xs font-bold text-white shadow-sm">
                                {user.name.charAt(0).toUpperCase()}
                            </div>
                            <span className="text-sm text-slate-700 font-medium hidden sm:inline">{user.name}</span>
                        </div>
                        {activeView === "chat" && (
                            <button
                                onClick={handleNewChat}
                                title="New Chat"
                                className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-colors"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        )}
                        <button
                            onClick={onLogout}
                            title="Sign out"
                            className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-red-500 transition-colors"
                        >
                            <LogOut className="w-4 h-4" />
                        </button>
                    </div>
                </header>

                {activeView === "knowledge" ? (
                    <KnowledgeBase onSelectionChange={setSelectedFiles} selectedFiles={selectedFiles} token={user?.token} />
                ) : activeView === "dashboard" ? (
                    <Dashboard />
                ) : activeView === "documentation" ? (
                    <Documentation />
                ) : activeView === "data-analysis" ? (
                    <DataAnalysisView user={user} />
                ) : activeView === "report-builder" ? (
                    <ReportBuilderView user={user} />
                ) : (
                    <>
                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6 light-scrollbar">
                            {messages.length === 0 && (
                                <motion.div
                                    initial={{ opacity: 0, y: 16 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                    className="flex flex-col items-center justify-center h-full text-center gap-6"
                                >
                                    <div className="relative">
                                        <div className="w-20 h-20 rounded-2xl bg-white border border-slate-200 flex items-center justify-center shadow-xl shadow-slate-200/50 backdrop-blur-sm">
                                            <Bot className="w-10 h-10 text-sky-500" />
                                        </div>
                                        <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-white" />
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-semibold text-slate-800 mb-1">
                                            Hello, <span className="gradient-text">{user.name}</span> 👋
                                        </h2>
                                        <p className="text-slate-500 text-sm max-w-xs">
                                            Ask me anything about your documents. I&apos;ll retrieve and reason over them for you.
                                        </p>
                                    </div>
                                    <div className="flex gap-2 flex-wrap justify-center">
                                        {(Object.entries(MODE_CONFIG) as [ChatMode, typeof MODE_CONFIG[ChatMode]][]).map(([m, cfg]) => (
                                            <button
                                                key={m}
                                                onClick={() => setMode(m)}
                                                title={cfg.description}
                                                className={cn(
                                                    "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all",
                                                    mode === m ? cn(cfg.bg, cfg.color) : "bg-white border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 shadow-sm"
                                                )}
                                            >
                                                <cfg.icon className="w-3 h-3" /> {cfg.label}
                                            </button>
                                        ))}
                                    </div>
                                </motion.div>
                            )}

                            {messages.map((msg, idx) => (
                                <motion.div
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.3 }}
                                    key={idx}
                                    className={cn(
                                        "w-full max-w-4xl mx-auto",
                                        msg.role === "user" ? "flex justify-end" : ""
                                    )}
                                >
                                    {msg.role === "user" ? (
                                        /* ── User bubble ─────────────────────────── */
                                        <div className="flex items-end gap-2.5 flex-row-reverse max-w-[75%]">
                                            <div className="w-7 h-7 rounded-full shrink-0 bg-gradient-to-br from-sky-400 to-blue-500 shadow-md shadow-sky-400/30 flex items-center justify-center">
                                                <span className="text-[10px] font-bold text-white">{user.name.charAt(0).toUpperCase()}</span>
                                            </div>
                                            <div className="px-4 py-3 text-sm leading-relaxed bg-gradient-to-br from-sky-400 to-blue-500 text-white rounded-2xl rounded-br-sm shadow-md shadow-sky-400/20">
                                                <p className="whitespace-pre-wrap">{msg.content}</p>
                                            </div>
                                        </div>
                                    ) : (
                                        /* ── Assistant full-width prose ─────────── */
                                        <div className="w-full flex flex-col gap-2 py-1">
                                            {/* Label row */}
                                            <div className="flex items-center gap-1.5 mb-0.5">
                                                <div className="w-5 h-5 rounded-full bg-sky-100 border border-sky-200 flex items-center justify-center">
                                                    <Bot className="w-3 h-3 text-sky-500" />
                                                </div>
                                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest">AI</span>
                                            </div>

                                            {/* Content */}
                                            {/* Thinking Panel (reasoning / deep_analytic) */}
                                            {msg.thinkingSteps && msg.thinkingSteps.length > 0 && (
                                                <ThinkingPanel
                                                    steps={msg.thinkingSteps}
                                                    isOpen={!!msg.thinkingOpen}
                                                    onToggle={() => toggleThinking(idx)}
                                                    isComplete={!!msg.isComplete}
                                                />
                                            )}

                                            {msg.content || msg.isThinking ? (
                                                <div className="flex flex-col gap-3">
                                                    {msg.isThinking && (
                                                        <div className="flex items-center gap-2 py-2 px-3 bg-sky-50/50 rounded-xl border border-sky-100/50 w-fit animate-pulse">
                                                            <div className="flex gap-1">
                                                                <span className="w-1 h-1 bg-sky-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                                                                <span className="w-1 h-1 bg-sky-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                                                                <span className="w-1 h-1 bg-sky-400 rounded-full animate-bounce" />
                                                            </div>
                                                            <span className="text-[10px] font-medium text-sky-500 uppercase tracking-wider">Thinking</span>
                                                        </div>
                                                    )}
                                                    {msg.content && (
                                                        <div className="text-sm leading-[1.8] text-slate-700 w-full prose prose-slate prose-sm max-w-none 
                                                            prose-p:leading-[1.8] prose-p:mb-4 
                                                            prose-headings:text-slate-900 prose-headings:font-bold prose-headings:mt-6 prose-headings:mb-3
                                                            prose-ul:my-4 prose-ul:list-disc prose-ul:pl-5
                                                            prose-ol:my-4 prose-ol:list-decimal prose-ol:pl-5
                                                            prose-li:my-1 prose-strong:text-slate-900 prose-strong:font-bold">
                                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                                {msg.content}
                                                            </ReactMarkdown>
                                                        </div>
                                                    )}
                                                    {msg.chartType && msg.chartData && (
                                                        <ChatChart chartType={msg.chartType} chartData={msg.chartData} />
                                                    )}
                                                </div>
                                            ) : (
                                                <div className="flex gap-1 items-center h-6">
                                                    <span className="w-1.5 h-1.5 bg-sky-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                                                    <span className="w-1.5 h-1.5 bg-sky-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                                                    <span className="w-1.5 h-1.5 bg-sky-400 rounded-full animate-bounce" />
                                                </div>
                                            )}

                                            {/* Citation — always show when complete & sources exist */}
                                            {msg.isComplete && msg.sources && msg.sources.length > 0 && (
                                                <div className="mt-4 pt-4 border-t border-slate-100">
                                                    <div className="flex items-center gap-1.5 mb-2.5">
                                                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Sources</span>
                                                    </div>
                                                    <div className="flex flex-wrap gap-1.5">
                                                        {msg.sources.map((src, sidx) => (
                                                            <div
                                                                key={sidx}
                                                                className="group relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200/60 hover:border-sky-200 hover:bg-sky-50/30 transition-all"
                                                                title={src.full_path || src.content || src.filename}
                                                            >
                                                                <div className={cn("shrink-0 w-1.5 h-1.5 rounded-full",
                                                                    msg.mode === "reasoning" ? "bg-amber-400" :
                                                                        msg.mode === "deep_analytic" ? "bg-cyan-400" :
                                                                            sidx % 2 === 0 ? "bg-sky-400" : "bg-blue-400"
                                                                )} />
                                                                <span className="text-[10px] font-medium text-slate-600 group-hover:text-sky-700 truncate max-w-[140px]">
                                                                    {src.filename}
                                                                </span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Metrics - Only show when complete */}
                                            {msg.isComplete && msg.metrics && (
                                                <div className="flex flex-wrap gap-2 mt-1">
                                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-[10px] text-slate-500">
                                                        ⏱ Latency: <span className="text-slate-700 font-medium">{msg.metrics.latency.toFixed(2)}s</span>
                                                    </span>
                                                    {msg.metrics.faithfulness != null && (
                                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-[10px] text-slate-500">
                                                            🎯 Faithful: <span className="text-slate-700 font-medium">{msg.metrics.faithfulness.toFixed(2)}</span>
                                                        </span>
                                                    )}
                                                    {msg.metrics.answer_relevancy != null && (
                                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-[10px] text-slate-500">
                                                            🔗 Relevance: <span className="text-slate-700 font-medium">{msg.metrics.answer_relevancy.toFixed(2)}</span>
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </motion.div>
                            ))}
                            <div ref={scrollRef} />
                        </div>

                        {/* Input Area */}
                        <div className="py-5 px-4 bg-gradient-to-t from-white via-white/95 to-transparent">
                            <form onSubmit={handleSubmit} className="relative max-w-4xl mx-auto w-full group">
                                <div className="bg-white border border-slate-200 shadow-sm shadow-slate-200/50 rounded-2xl flex flex-col focus-within:border-sky-300 focus-within:ring-4 focus-within:ring-sky-500/10 transition-all">
                                    <textarea
                                        value={input}
                                        onChange={(e) => setInput(e.target.value)}
                                        placeholder="Ask anything about your documents…"
                                        className="w-full bg-transparent px-5 py-4 text-sm text-slate-900 focus:outline-none placeholder:text-slate-400 resize-none min-h-[56px] max-h-48"
                                        rows={Math.min(5, Math.max(1, input.split("\n").length))}
                                        disabled={isLoading}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault();
                                                if (input.trim() && !isLoading) handleSubmit(e);
                                            }
                                        }}
                                    />

                                    <div className="flex items-center justify-between px-3 pb-3">
                                        {/* Mode Dropdown & Private Toggle */}
                                        <div className="flex gap-2 flex-wrap items-center relative">
                                            {/* Mode Selector Button */}
                                            <div className="relative">
                                                <button
                                                    type="button"
                                                    onClick={() => setIsModeMenuOpen(!isModeMenuOpen)}
                                                    className={cn(
                                                        "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-200 shadow-sm",
                                                        MODE_CONFIG[mode].bg,
                                                        MODE_CONFIG[mode].color
                                                    )}
                                                >
                                                    {(() => {
                                                        const Icon = MODE_CONFIG[mode].icon;
                                                        return <Icon className="w-3.5 h-3.5" />;
                                                    })()}
                                                    <span className="capitalize">Mode: {MODE_CONFIG[mode].label}</span>
                                                    <ChevronUp className={cn("w-3.5 h-3.5 transition-transform", isModeMenuOpen ? "rotate-180" : "")} />
                                                </button>

                                                {/* Dropdown Menu */}
                                                <AnimatePresence>
                                                    {isModeMenuOpen && (
                                                        <motion.div
                                                            initial={{ opacity: 0, y: 10 }}
                                                            animate={{ opacity: 1, y: 0 }}
                                                            exit={{ opacity: 0, y: 10 }}
                                                            transition={{ duration: 0.15 }}
                                                            className="absolute bottom-full mb-2 left-0 w-48 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden z-50"
                                                        >
                                                            <div className="py-1">
                                                                {(Object.entries(MODE_CONFIG) as [ChatMode, typeof MODE_CONFIG[ChatMode]][]).map(([m, cfg]) => (
                                                                    <button
                                                                        key={m}
                                                                        type="button"
                                                                        onClick={() => {
                                                                            setMode(m);
                                                                            setIsModeMenuOpen(false);
                                                                        }}
                                                                        className={cn(
                                                                            "w-full flex items-start gap-2 px-3 py-2 text-left hover:bg-slate-50 transition-colors",
                                                                            mode === m ? "bg-slate-50" : ""
                                                                        )}
                                                                    >
                                                                        <div className={cn("p-1.5 rounded-lg shrink-0", mode === m ? cfg.bg : "bg-slate-100")}>
                                                                            <cfg.icon className={cn("w-3.5 h-3.5", mode === m ? cfg.color : "text-slate-500")} />
                                                                        </div>
                                                                        <div>
                                                                            <div className={cn("text-xs font-semibold", mode === m ? cfg.color : "text-slate-700")}>
                                                                                {cfg.label}
                                                                            </div>
                                                                            <div className="text-[10px] text-slate-500 leading-tight mt-0.5">
                                                                                {cfg.description}
                                                                            </div>
                                                                        </div>
                                                                    </button>
                                                                ))}
                                                            </div>
                                                        </motion.div>
                                                    )}
                                                </AnimatePresence>
                                            </div>

                                            <div className="w-px h-5 bg-slate-200 mx-1 hidden sm:block" />

                                            <button
                                                type="button"
                                                onClick={() => setUseOllama(!useOllama)}
                                                className={cn(
                                                    "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-200",
                                                    useOllama
                                                        ? "bg-emerald-50 border-emerald-300 text-emerald-700 shadow-sm"
                                                        : "bg-white border-slate-200 text-slate-500 hover:text-slate-700 hover:bg-slate-50"
                                                )}
                                                title="Enable Secure Local Model (Ollama)"
                                            >
                                                <div className={cn("w-2 h-2 rounded-full", useOllama ? "bg-emerald-500 animate-pulse" : "bg-slate-300")} />
                                                Private: {useOllama ? "ON" : "OFF"}
                                            </button>
                                        </div>

                                        <button
                                            type="submit"
                                            disabled={isLoading || !input.trim()}
                                            className="w-10 h-10 flex items-center justify-center bg-white border border-slate-200 rounded-full text-blue-600 shadow-sm hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all hover:scale-105 active:scale-95 shrink-0"
                                        >
                                            <Send className="w-5 h-5 ml-0.5" />
                                        </button>
                                    </div>
                                </div>
                            </form>
                            <p className="text-center text-[10px] text-slate-400 mt-3 font-medium">
                                AI responses may contain errors · Always verify critical information
                            </p>
                        </div>
                    </>
                )}
            </div>
        </div >
    );
}
