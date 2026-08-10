"use client";

import { useState, useRef, useEffect } from "react";
import {
    FolderOpen, MessageSquare, Upload, FileText,
    Plus, Clock, ChevronLeft, ChevronRight, ChevronDown, LogOut, Database, Activity,
    BookOpen, BarChart2, LayoutDashboard, Settings
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Session, FileItem } from "@/types/chat";
import { motion, AnimatePresence } from "framer-motion";
import { AuthUser } from "@/lib/useAuth";
import SettingsModal from "./SettingsModal";

interface SidebarProps {
    sessions: Session[];
    currentSessionId: string | null;
    onSelectSession: (id: string) => void;
    onNewChat: () => void;
    user: AuthUser;
    onLogout: () => void;
    activeView: "chat" | "knowledge" | "dashboard" | "documentation" | "data-analysis" | "report-builder";
    onViewChange: (view: "chat" | "knowledge" | "dashboard" | "documentation" | "data-analysis" | "report-builder") => void;
}

const FILE_EXT_COLORS: Record<string, string> = {
    pdf: "text-red-400 bg-red-400/10",
    txt: "text-blue-400 bg-blue-400/10",
    md: "text-purple-400 bg-purple-400/10",
    doc: "text-emerald-500 bg-emerald-500/10",
    docx: "text-emerald-500 bg-emerald-500/10",
    png: "text-amber-500 bg-amber-500/10",
    jpg: "text-amber-500 bg-amber-500/10",
    jpeg: "text-amber-500 bg-amber-500/10",
    webp: "text-amber-500 bg-amber-500/10",
    bmp: "text-amber-500 bg-amber-500/10",
};

function getFileColor(filename: string) {
    const ext = filename.split(".").pop()?.toLowerCase() ?? "";
    return FILE_EXT_COLORS[ext] ?? "text-slate-500 bg-slate-500/10";
}

export default function Sidebar({
    sessions, currentSessionId,
    onSelectSession, onNewChat,
    user, onLogout,
    activeView, onViewChange
}: SidebarProps) {
    const [isOpen, setIsOpen] = useState(true);
    const [mounted, setMounted] = useState(false);
    const [isChatExpanded, setIsChatExpanded] = useState(true);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    useEffect(() => { setMounted(true); }, []);

    const formatDate = (timestamp: string) => {
        if (!mounted) return "";
        try {
            const d = new Date(timestamp);
            const now = new Date();
            const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000);
            if (diffDays === 0) return "Today";
            if (diffDays === 1) return "Yesterday";
            return d.toLocaleDateString();
        } catch { return ""; }
    };



    return (
        <>
            <AnimatePresence mode="wait">
                {isOpen && (
                    <motion.div
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 280, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                        className="h-full shrink-0 relative z-20 py-4 pl-4 pr-2"
                    >
                        <div className="h-full w-full bg-white/95 backdrop-blur-md flex flex-col min-h-0 overflow-hidden shadow-[0_8px_30px_rgb(0,0,0,0.06)] rounded-[2rem] border border-white">
                            {/* Brand Header */}
                            <div className="pt-7 px-4 pb-4 border-b border-slate-100/60 bg-transparent">
                                <div className="flex items-center gap-2.5">
                                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-600 to-blue-500 flex items-center justify-center shadow-md shadow-blue-500/20 text-white font-bold text-xs">
                                        KMI
                                    </div>
                                    <div>
                                        <h1 className="text-sm font-bold text-slate-800 leading-none truncate">Knowlytic Intelligence</h1>
                                        <p className="text-[10px] text-slate-500 leading-none mt-0.5 truncate">Document and Data Intelligence</p>
                                    </div>
                                </div>
                            </div>

                            {/* Navigation Menu */}
                            <div className="flex-1 min-h-0 overflow-y-auto hidden-scrollbar p-3 pb-0 space-y-2 z-10">
                                <button
                                    onClick={() => onViewChange("documentation")}
                                    className={cn(
                                        "w-full py-1.5 px-2 rounded-2xl transition-all flex items-center gap-3 text-sm font-bold",
                                        activeView === "documentation"
                                            ? "text-slate-800"
                                            : "text-slate-500 hover:text-slate-800"
                                    )}
                                >
                                    <div className={cn(
                                        "w-10 h-10 rounded-full flex items-center justify-center transition-all shrink-0",
                                        activeView === "documentation"
                                            ? "bg-white shadow-md shadow-blue-500/10 text-blue-600"
                                            : "bg-blue-500/5 text-slate-400 hover:bg-white hover:shadow-sm hover:text-blue-500"
                                    )}>
                                        <BookOpen className="w-5 h-5" />
                                    </div>
                                    Overview
                                </button>

                                <button
                                    onClick={() => onViewChange("knowledge")}
                                    className={cn(
                                        "w-full py-1.5 px-2 rounded-2xl transition-all flex items-center gap-3 text-sm font-bold",
                                        activeView === "knowledge"
                                            ? "text-slate-800"
                                            : "text-slate-500 hover:text-slate-800"
                                    )}
                                >
                                    <div className={cn(
                                        "w-10 h-10 rounded-full flex items-center justify-center transition-all shrink-0",
                                        activeView === "knowledge"
                                            ? "bg-white shadow-md shadow-blue-500/10 text-blue-600"
                                            : "bg-blue-500/5 text-slate-400 hover:bg-white hover:shadow-sm hover:text-blue-500"
                                    )}>
                                        <Database className="w-5 h-5" />
                                    </div>
                                    Knowledge Base
                                </button>

                                <button
                                    onClick={() => onViewChange("data-analysis")}
                                    className={cn(
                                        "w-full py-1.5 px-2 rounded-2xl transition-all flex items-center gap-3 text-sm font-bold",
                                        activeView === "data-analysis"
                                            ? "text-slate-800"
                                            : "text-slate-500 hover:text-slate-800"
                                    )}
                                >
                                    <div className={cn(
                                        "w-10 h-10 rounded-full flex items-center justify-center transition-all shrink-0",
                                        activeView === "data-analysis"
                                            ? "bg-white shadow-md shadow-blue-500/10 text-blue-600"
                                            : "bg-blue-500/5 text-slate-400 hover:bg-white hover:shadow-sm hover:text-blue-500"
                                    )}>
                                        <BarChart2 className="w-5 h-5" />
                                    </div>
                                    Data Analysis
                                </button>

                                <button
                                    onClick={() => onViewChange("report-builder")}
                                    className={cn(
                                        "w-full py-1.5 px-2 rounded-2xl transition-all flex items-center gap-3 text-sm font-bold",
                                        activeView === "report-builder"
                                            ? "text-slate-800"
                                            : "text-slate-500 hover:text-slate-800"
                                    )}
                                >
                                    <div className={cn(
                                        "w-10 h-10 rounded-full flex items-center justify-center transition-all shrink-0",
                                        activeView === "report-builder"
                                            ? "bg-white shadow-md shadow-blue-500/10 text-blue-600"
                                            : "bg-blue-500/5 text-slate-400 hover:bg-white hover:shadow-sm hover:text-blue-500"
                                    )}>
                                        <LayoutDashboard className="w-5 h-5" />
                                    </div>
                                    Report Builder
                                </button>
                                <button
                                    onClick={() => onViewChange("dashboard")}
                                    className={cn(
                                        "w-full py-1.5 px-2 rounded-2xl transition-all flex items-center gap-3 text-sm font-bold",
                                        activeView === "dashboard"
                                            ? "text-slate-800"
                                            : "text-slate-500 hover:text-slate-800"
                                    )}
                                >
                                    <div className={cn(
                                        "w-10 h-10 rounded-full flex items-center justify-center transition-all shrink-0",
                                        activeView === "dashboard"
                                            ? "bg-white shadow-md shadow-blue-500/10 text-blue-600"
                                            : "bg-blue-500/5 text-slate-400 hover:bg-white hover:shadow-sm hover:text-blue-500"
                                    )}>
                                        <Activity className="w-5 h-5" />
                                    </div>
                                    Dashboard Metrics
                                </button>




                                <div className="pt-2 border-t border-blue-100/50 mt-2">
                                    <button
                                        onClick={() => setIsChatExpanded(!isChatExpanded)}
                                        className="w-full py-1.5 px-2 rounded-2xl transition-all flex items-center justify-between text-sm font-bold text-slate-700 hover:text-slate-900 group"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full flex items-center justify-center transition-all bg-blue-500/5 text-blue-500 group-hover:bg-white group-hover:shadow-sm">
                                                <MessageSquare className="w-5 h-5" />
                                            </div>
                                            <span>Chatbot Knowledge</span>
                                        </div>
                                        <ChevronDown className={cn("w-4 h-4 text-slate-400 transition-transform mr-2", !isChatExpanded && "-rotate-90")} />
                                    </button>

                                    <AnimatePresence>
                                        {isChatExpanded && (
                                            <motion.div
                                                initial={{ height: 0, opacity: 0 }}
                                                animate={{ height: "auto", opacity: 1 }}
                                                exit={{ height: 0, opacity: 0 }}
                                                className="overflow-hidden"
                                            >
                                                <div className="pl-5 pr-1 py-2 space-y-2 mt-1">
                                                    <button
                                                        onClick={() => {
                                                            onViewChange("chat");
                                                            onNewChat();
                                                        }}
                                                        className={cn(
                                                            "w-full py-2 px-3 rounded-xl transition-all flex items-center gap-2 text-xs font-semibold",
                                                            activeView === "chat" && !currentSessionId
                                                                ? "bg-blue-50 text-blue-700 border border-blue-200"
                                                                : "text-slate-600 border border-dashed border-slate-300 hover:text-blue-600 hover:border-blue-400 hover:bg-white"
                                                        )}
                                                    >
                                                        <Plus className="w-3.5 h-3.5" />
                                                        New Conversation
                                                    </button>

                                                    <div className="max-h-[30vh] overflow-y-auto pr-1 light-scrollbar space-y-1">
                                                        {sessions.length === 0 ? (
                                                            <div className="flex flex-col items-center justify-center py-4 text-center">
                                                                <p className="text-[10px] text-slate-400">No conversations</p>
                                                            </div>
                                                        ) : (
                                                            sessions.map((session) => (
                                                                <button
                                                                    key={session.id}
                                                                    onClick={() => {
                                                                        onViewChange("chat");
                                                                        onSelectSession(session.id);
                                                                    }}
                                                                    className={cn(
                                                                        "w-full p-2.5 rounded-lg text-left transition-all group relative border",
                                                                        activeView === "chat" && currentSessionId === session.id
                                                                            ? "bg-white border-blue-200 text-blue-900 shadow-sm"
                                                                            : "hover:bg-white/80 text-slate-600 hover:text-slate-900 border-transparent"
                                                                    )}
                                                                >
                                                                    {activeView === "chat" && currentSessionId === session.id && (
                                                                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-3/4 bg-blue-500 rounded-r-full" />
                                                                    )}
                                                                    <p className="text-[11px] font-medium truncate">{session.title}</p>
                                                                    <div className="flex items-center gap-1 mt-0.5 text-[9px] text-slate-400 font-medium">
                                                                        <Clock className="w-2.5 h-2.5" />
                                                                        {formatDate(session.timestamp)}
                                                                    </div>
                                                                </button>
                                                            ))
                                                        )}
                                                    </div>
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>
                            </div>

                            {/* User Footer */}
                            <div className="p-3 border-t border-blue-100/50 bg-white/50 backdrop-blur-sm z-20">
                                <div className="flex items-center gap-2.5 px-2 py-2 rounded-xl hover:bg-white shadow-sm transition-all group border border-transparent hover:border-blue-100">
                                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-xs font-bold text-white shadow-sm shrink-0">
                                        {user.name.charAt(0).toUpperCase()}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-bold text-slate-800 truncate">{user.name}</p>
                                        <p className="text-[10px] font-medium text-slate-500 truncate">{user.email}</p>
                                    </div>
                                    <div className="flex opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={() => setIsSettingsOpen(true)}
                                            title="Settings"
                                            className="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                                        >
                                            <Settings className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={onLogout}
                                            title="Sign out"
                                            className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                                        >
                                            <LogOut className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Toggle button */}
            <motion.button
                onClick={() => setIsOpen(!isOpen)}
                animate={{ left: isOpen ? 284 : 16 }}
                transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                className="absolute top-1/2 -translate-y-1/2 z-50 p-1.5 bg-white/50 backdrop-blur-md rounded-full text-slate-400 hover:text-blue-600 hover:bg-white transition-all shadow-sm hover:shadow-md border border-white/50"
                style={{ left: isOpen ? 284 : 16 }}
            >
                {isOpen ? <ChevronLeft className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </motion.button>
            
            <SettingsModal 
                isOpen={isSettingsOpen} 
                onClose={() => setIsSettingsOpen(false)} 
                user={user} 
            />
        </>
    );
}
