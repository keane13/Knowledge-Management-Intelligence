"use client";

import { useState, useRef, useEffect } from "react";
import { API_URL } from "@/lib/utils";
import {
    LayoutDashboard, Activity, CheckCircle2, Bot,
    FileText, Download, Loader2, ArrowRight, Clock
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { AuthUser } from "@/lib/useAuth";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ReportBuilderViewProps {
    user: AuthUser;
}

type Phase = "IDLE" | "PLANNING" | "EXTRACTING" | "WRITING" | "REFLECTING" | "DONE";

export default function ReportBuilderView({ user }: ReportBuilderViewProps) {
    const [prompt, setPrompt] = useState("");
    const [phase, setPhase] = useState<Phase>("IDLE");
    const [statusMessage, setStatusMessage] = useState("");
    const [extractionDetails, setExtractionDetails] = useState<string[]>([]);
    const [reportContent, setReportContent] = useState("");
    const [error, setError] = useState<string | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const [historyList, setHistoryList] = useState<{ id: string, report_title: string, timestamp: string }[]>([]);

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const response = await fetch(`${API_URL}/report/history`, {
                    headers: { "Authorization": `Bearer ${user.token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    setHistoryList(data);
                }
            } catch (err) {
                console.error("Failed to fetch report history:", err);
            }
        };
        fetchHistory();
    }, [user.token]);

    // Auto-scroll to bottom of report during streaming
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [reportContent]);

    const handleBuildReport = async () => {
        if (!prompt.trim()) return;

        setPhase("PLANNING");
        setStatusMessage("Menganalisis permintaan...");
        setExtractionDetails([]);
        setReportContent("");
        setError(null);

        try {
            const response = await fetch(`${API_URL}/report/build`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${user.token}`
                },
                body: JSON.stringify({
                    prompt: prompt,
                    session_id: `report_${Date.now()}`
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Gagal menghubungi server");
            }

            if (!response.body) throw new Error("No response body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const dataStr = line.substring(6).trim();
                        if (!dataStr) continue;

                        try {
                            const data = JSON.parse(dataStr);

                            if (data.type === "status") {
                                setPhase(data.status);
                                if (data.message) setStatusMessage(data.message);
                            } else if (data.type === "extraction_update") {
                                setExtractionDetails(prev => [...prev, data.detail]);
                            } else if (data.type === "chunk") {
                                setReportContent(prev => prev + data.content);
                            } else if (data.type === "error") {
                                setError(data.message || "Terjadi kesalahan saat menyusun laporan");
                                setPhase("IDLE");
                            } else if (data.type === "done") {
                                setPhase("DONE");
                                setStatusMessage("Laporan Selesai");
                            }
                        } catch (e) {
                            console.error("Error parsing JSON:", e, "Raw data:", dataStr);
                        }
                    }
                }
            }
        } catch (err: any) {
            console.error("Build report error:", err);
            setError(err.message || "Terjadi kesalahan saat menyusun laporan");
            setPhase("IDLE");
        }
    };

    const handleDownloadMarkdown = () => {
        const element = document.createElement("a");
        const file = new Blob([reportContent], { type: 'text/markdown' });
        element.href = URL.createObjectURL(file);
        element.download = "report.md";
        document.body.appendChild(element);
        element.click();
    };

    const handleDownloadWord = () => {
        const preHtml = "<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'><head><meta charset='utf-8'><title>Report</title></head><body>";
        const postHtml = "</body></html>";
        const content = document.getElementById("report-content-body")?.innerHTML || "";
        const html = preHtml + content + postHtml;

        const blob = new Blob(['\ufeff', html], { type: 'application/msword' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'report.doc';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleDownloadPDF = async () => {
        const element = document.getElementById("report-content-body");
        if (!element) return;
        
        // Dynamically import to avoid Next.js SSR issues with html2pdf
        const html2pdf = (await import('html2pdf.js')).default;
        
        const opt = {
            margin:       0.5,
            filename:     'report.pdf',
            image:        { type: 'jpeg' as const, quality: 0.98 },
            html2canvas:  { scale: 2 },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' as const }
        };

        html2pdf().set(opt).from(element).save();
    };

    const loadHistoryItem = async (id: string) => {
        setPhase("PLANNING");
        setStatusMessage("Memuat laporan...");
        setExtractionDetails([]);
        setReportContent("");
        setError(null);
        try {
            const response = await fetch(`${API_URL}/report/history/${id}`, {
                headers: { "Authorization": `Bearer ${user.token}` }
            });
            if (!response.ok) throw new Error("Gagal memuat riwayat");
            const data = await response.json();
            setReportContent(data.content || "*Laporan kosong*");
            setPrompt(data.report_title);
            setPhase("DONE");
            setStatusMessage("Laporan Dimuat");
        } catch (err: any) {
            setError(err.message);
            setPhase("IDLE");
        }
    };

    return (
        <div className="flex-1 flex overflow-hidden w-full relative z-10 bg-slate-50">
            {/* History Sidebar */}
            <div className="w-72 border-r border-slate-200 bg-white flex flex-col h-full hidden md:flex shrink-0">
                <div className="p-4 border-b border-slate-200">
                    <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                        <Clock className="w-4 h-4 text-slate-500" />
                        Riwayat Report
                    </h3>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    {historyList.length === 0 ? (
                        <p className="text-sm text-slate-500 text-center p-4">Belum ada riwayat</p>
                    ) : (
                        historyList.map(item => (
                            <button
                                key={item.id}
                                onClick={() => loadHistoryItem(item.id)}
                                className="w-full text-left p-3 hover:bg-slate-50 rounded-xl transition-colors group flex items-start gap-3"
                            >
                                <div className="bg-blue-100 p-2 rounded-lg text-blue-600 mt-0.5">
                                    <FileText className="w-4 h-4" />
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-slate-700 truncate w-44">{item.report_title}</p>
                                    <p className="text-xs text-slate-400 mt-1">{new Date(item.timestamp).toLocaleDateString()}</p>
                                </div>
                            </button>
                        ))
                    )}
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-y-auto w-full relative z-10 light-scrollbar p-6 lg:p-10 flex flex-col">

                {/* Header */}
                <div className="max-w-5xl mx-auto w-full mb-10 text-center shrink-0">
                    <div className="inline-flex items-center justify-center p-3 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl shadow-lg shadow-blue-500/20 mb-4">
                        <LayoutDashboard className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold text-slate-800 mb-2">Autonomous Report Builder</h1>
                    <p className="text-slate-500 text-sm max-w-lg mx-auto">
                        Kombinasikan data dari Database (SQL) dan Dokumen (RAG) secara otomatis menjadi laporan komprehensif.
                    </p>
                </div>

                <div className="max-w-5xl mx-auto w-full flex-1 flex flex-col gap-6">

                    {/* Input Area (Only show if IDLE) */}
                    {phase === "IDLE" && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                            className="bg-white p-6 rounded-3xl shadow-sm border border-slate-200"
                        >
                            <h3 className="text-lg font-bold text-slate-800 mb-4">Apa yang ingin Anda buat?</h3>
                            <textarea
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                placeholder="Contoh: Buatkan laporan yang membandingkan pendapatan Q3 vs Q4 dari database, lalu integrasikan dengan strategi marketing dari dokumen SOP."
                                className="w-full h-32 p-4 bg-slate-50 border border-slate-200 rounded-xl resize-none outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all text-sm text-slate-700"
                            />
                            {error && (
                                <div className="mt-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                                    {error}
                                </div>
                            )}
                            <div className="mt-4 flex justify-end">
                                <button
                                    onClick={handleBuildReport}
                                    disabled={!prompt.trim()}
                                    className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all shadow-md shadow-blue-500/20"
                                >
                                    Mulai Build Laporan
                                    <ArrowRight className="w-4 h-4" />
                                </button>
                            </div>
                        </motion.div>
                    )}

                    {/* Progress Indicators */}
                    {phase !== "IDLE" && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                            className="bg-white p-6 rounded-3xl shadow-sm border border-slate-200 flex flex-col gap-4 shrink-0"
                        >
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="font-bold text-slate-800 flex items-center gap-2">
                                    <Activity className="w-5 h-5 text-blue-500" />
                                    {statusMessage}
                                </h3>
                                {phase !== "DONE" && <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />}
                            </div>

                            <div className="flex justify-between relative">
                                {/* Line connecting steps */}
                                <div className="absolute top-1/2 left-0 w-full h-1 bg-slate-100 -translate-y-1/2 z-0"></div>
                                <div className="absolute top-1/2 left-0 h-1 bg-blue-500 -translate-y-1/2 z-0 transition-all duration-500"
                                    style={{
                                        width: phase === "PLANNING" ? '10%' :
                                            phase === "EXTRACTING" ? '30%' :
                                                phase === "WRITING" ? '55%' : 
                                                    phase === "REFLECTING" ? '80%' : '100%'
                                    }}>
                                </div>

                                {/* Steps */}
                                {[
                                    { id: "PLANNING", label: "Perencanaan", icon: Bot },
                                    { id: "EXTRACTING", label: "Ekstraksi Data", icon: Activity },
                                    { id: "WRITING", label: "Sintesis Laporan", icon: FileText },
                                    { id: "REFLECTING", label: "Refleksi & Poles", icon: Bot },
                                    { id: "DONE", label: "Selesai", icon: CheckCircle2 }
                                ].map((step, idx) => {
                                    const isActive = phase === step.id;
                                    const isPast = ["DONE", "REFLECTING", "WRITING", "EXTRACTING", "PLANNING"].indexOf(phase) <= ["DONE", "REFLECTING", "WRITING", "EXTRACTING", "PLANNING"].indexOf(step.id);

                                    return (
                                        <div key={step.id} className="relative z-10 flex flex-col items-center gap-2">
                                            <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all ${isActive ? "bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-500/30" :
                                                    isPast ? "bg-blue-500 border-blue-500 text-white" : "bg-white border-slate-200 text-slate-300"
                                                }`}>
                                                <step.icon className="w-5 h-5" />
                                            </div>
                                            <span className={`text-xs font-bold ${isActive ? "text-blue-700" : isPast ? "text-blue-500" : "text-slate-400"}`}>
                                                {step.label}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Extraction Details Log */}
                            {phase === "EXTRACTING" && extractionDetails.length > 0 && (
                                <div className="mt-4 p-4 bg-slate-50 border border-slate-100 rounded-xl max-h-32 overflow-y-auto light-scrollbar">
                                    <ul className="space-y-2">
                                        {extractionDetails.map((detail, idx) => (
                                            <li key={idx} className="text-xs font-medium text-slate-500 flex items-center gap-2">
                                                <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                                                {detail}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </motion.div>
                    )}

                    {/* Report Output Area */}
                    {(phase === "WRITING" || phase === "REFLECTING" || phase === "DONE") && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                            className="bg-white rounded-3xl shadow-sm border border-slate-200 flex flex-col flex-1 min-h-[500px] overflow-hidden"
                        >
                            <div className="bg-slate-50 border-b border-slate-200 p-4 flex flex-wrap items-center justify-between shrink-0 gap-4">
                                <h3 className="font-bold text-slate-700 flex items-center gap-2">
                                    <FileText className="w-5 h-5 text-blue-500" />
                                    Hasil Laporan
                                </h3>
                                {phase === "DONE" && (
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={handleDownloadPDF}
                                            className="flex items-center gap-2 px-3 py-1.5 bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 rounded-lg text-sm font-medium transition-colors shadow-sm"
                                        >
                                            <Download className="w-4 h-4" />
                                            PDF
                                        </button>
                                        <button
                                            onClick={handleDownloadWord}
                                            className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-600 border border-blue-200 hover:bg-blue-100 rounded-lg text-sm font-medium transition-colors shadow-sm"
                                        >
                                            <Download className="w-4 h-4" />
                                            Word
                                        </button>
                                        <button
                                            onClick={handleDownloadMarkdown}
                                            className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg text-sm font-medium text-slate-600 transition-colors shadow-sm"
                                        >
                                            <Download className="w-4 h-4" />
                                            .md
                                        </button>
                                    </div>
                                )}
                            </div>
                            <div
                                ref={scrollRef}
                                className="p-8 overflow-y-auto prose prose-slate max-w-none text-slate-700 prose-headings:text-blue-900 prose-a:text-blue-600 prose-table:border prose-th:bg-slate-100 prose-th:p-2 prose-td:p-2 prose-td:border-t flex-1"
                            >
                                <div id="report-content-body">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {reportContent || "*Menyusun laporan...*"}
                                    </ReactMarkdown>
                                </div>
                                {(phase === "WRITING" || phase === "REFLECTING") && (
                                    <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse"></span>
                                )}
                            </div>
                        </motion.div>
                    )}

                    {phase === "DONE" && (
                        <div className="flex justify-center pb-10">
                            <button
                                onClick={() => setPhase("IDLE")}
                                className="px-6 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 font-medium rounded-xl transition-colors shadow-sm"
                            >
                                Buat Laporan Baru
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>

    );
}
