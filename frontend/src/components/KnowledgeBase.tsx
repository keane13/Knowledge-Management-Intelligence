"use client";

import { useState, useRef, useEffect } from "react";
import {
    FileText, Trash2, Zap, Upload, Database, CheckCircle2, ChevronDown, Folder, Plus, FileImage, FileAudio, X, Eye
} from "lucide-react";
import { cn } from "@/lib/utils";
import { FileItem } from "@/types/chat";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface KnowledgeBaseProps {
    onSelectionChange: (selectedFiles: string[]) => void;
    selectedFiles: string[];
}

export default function KnowledgeBase({ onSelectionChange, selectedFiles }: KnowledgeBaseProps) {
    const [files, setFiles] = useState<FileItem[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [summary, setSummary] = useState<{ filename: string; text: string } | null>(null);
    const [isSummarizing, setIsSummarizing] = useState<string | null>(null);
    const [viewingFile, setViewingFile] = useState<string | null>(null);
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
    const [uploadFolder, setUploadFolder] = useState("");
    const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
    
    const docInputRef = useRef<HTMLInputElement>(null);
    const imgInputRef = useRef<HTMLInputElement>(null);
    const audioInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        fetchFiles();
    }, []);

    const fetchFiles = async () => {
        try {
            const res = await fetch("http://localhost:8000/files");
            const data = await res.json();
            const fileList = (data.files || []).map((f: any) => {
                if (typeof f === 'string') {
                    return { filename: f, checked: selectedFiles.includes(f) };
                }
                return {
                    filename: f.filename,
                    size: f.size,
                    updated: f.updated,
                    checked: selectedFiles.includes(f.filename)
                };
            });
            setFiles(fileList);
        } catch (e) {
            console.error(e);
        }
    };

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        setIsUploadModalOpen(false);
        const formData = new FormData();
        formData.append("file", file);
        if (uploadFolder.trim()) {
            formData.append("folder", uploadFolder.trim());
        }
        try {
            const res = await fetch("http://localhost:8000/upload", { method: "POST", body: formData });
            if (res.ok) fetchFiles();
        } catch (e) {
            console.error(e);
        } finally {
            setIsUploading(false);
            setUploadFolder("");
            e.target.value = "";
        }
    };

    const handleToggleFile = (filename: string) => {
        setFiles(prev => {
            const updated = prev.map(f => f.filename === filename ? { ...f, checked: !f.checked } : f);
            const selected = updated.filter(f => f.checked).map(f => f.filename);
            onSelectionChange(selected);
            return updated;
        });
    };

    const handleDeleteFile = async (e: React.MouseEvent, filename: string) => {
        e.preventDefault();
        e.stopPropagation();
        if (!confirm(`Are you sure you want to delete "${filename}"? This will also remove it from the search index.`)) return;

        try {
            const res = await fetch(`http://localhost:8000/files/${filename}`, { method: "DELETE" });
            if (res.ok) {
                setFiles(prev => {
                    const updated = prev.filter(f => f.filename !== filename);
                    const selected = updated.filter(f => f.checked).map(f => f.filename);
                    onSelectionChange(selected);
                    return updated;
                });
            } else {
                const err = await res.json();
                alert(`Error: ${err.detail || "Failed to delete file"}`);
            }
        } catch (e) {
            console.error(e);
            alert("Network error while deleting file");
        }
    };

    const handleSummarizeFile = async (e: React.MouseEvent, filename: string) => {
        e.preventDefault();
        e.stopPropagation();
        setIsSummarizing(filename);
        try {
            const res = await fetch(`http://localhost:8000/files/${filename}/summarize`, { method: "POST" });
            if (res.ok) {
                const data = await res.json();
                setSummary({ filename, text: data.summary });
            } else {
                const err = await res.json();
                alert(`Error: ${err.detail || "Failed to summarize file"}`);
            }
        } catch (e) {
            console.error(e);
            alert("Network error while summarizing file");
        } finally {
            setIsSummarizing(null);
        }
    };

    const getFileColor = (filename: string) => {
        const ext = filename.split(".").pop()?.toLowerCase() ?? "";
        const colors: Record<string, string> = {
            pdf: "text-red-500 bg-red-50 border-red-100",
            txt: "text-blue-500 bg-blue-50 border-blue-100",
            md: "text-purple-500 bg-purple-50 border-purple-100",
            doc: "text-emerald-600 bg-emerald-50 border-emerald-100",
            docx: "text-emerald-600 bg-emerald-50 border-emerald-100",
            png: "text-amber-500 bg-amber-50 border-amber-100",
            jpg: "text-amber-500 bg-amber-50 border-amber-100",
            jpeg: "text-amber-500 bg-amber-50 border-amber-100",
            webp: "text-amber-500 bg-amber-50 border-amber-100",
            bmp: "text-amber-500 bg-amber-50 border-amber-100",
        };
        return colors[ext] ?? "text-slate-500 bg-slate-50 border-slate-200";
    };

    return (
        <div className="flex-1 overflow-y-auto w-full flex flex-col items-center">
            <div className="w-full max-w-6xl py-10 px-6 sm:px-8 lg:px-10">
                {/* Unified Header Card */}
                <div className="bg-white rounded-3xl border border-slate-200/60 shadow-sm p-8 mb-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">Knowledge Base</h2>
                        <p className="text-slate-500 mt-2 text-lg">Manage and select documents or images to provide context for AI reasoning.</p>
                    </div>

                    <div className="shrink-0 relative">
                        <input type="file" ref={docInputRef} onChange={handleUpload} className="hidden" accept=".pdf,.txt,.md,.doc,.docx" />
                        <input type="file" ref={imgInputRef} onChange={handleUpload} className="hidden" accept=".png,.jpg,.jpeg,.webp,.bmp" />
                        <input type="file" ref={audioInputRef} onChange={handleUpload} className="hidden" accept=".mp3,.wav,.m4a" />
                        
                        <button
                            onClick={() => setIsUploadModalOpen(true)}
                            disabled={isUploading}
                            className="h-12 px-8 rounded-2xl bg-slate-800 hover:bg-slate-700 text-white transition-all flex items-center justify-center gap-3 text-sm font-bold shadow-lg shadow-slate-200 disabled:opacity-50 hover:shadow-xl hover:-translate-y-0.5 active:scale-95"
                        >
                            {isUploading ? (
                                <span className="animate-pulse flex items-center gap-2">
                                    <span className="w-2 h-2 bg-white/80 rounded-full animate-bounce" />
                                    Uploading…
                                </span>
                            ) : (
                                <><Plus className="w-5 h-5" /> Add Source</>
                            )}
                        </button>
                    </div>
                </div>

                {files.length === 0 ? (
                    <div className="bg-white/50 border-2 border-slate-200 border-dashed rounded-[3rem] p-24 flex flex-col items-center justify-center text-center">
                        <div className="w-24 h-24 bg-blue-50 rounded-3xl flex items-center justify-center mb-8">
                            <Database className="w-12 h-12 text-blue-400" />
                        </div>
                        <h3 className="text-2xl font-bold text-slate-800 mb-2">No documents yet</h3>
                        <p className="text-slate-500 max-w-md mb-8 text-lg">Upload PDFs, text, or images to start building your knowledge base.</p>
                        <button
                            onClick={() => setIsUploadModalOpen(true)}
                            className="text-blue-600 font-bold hover:text-blue-700 text-lg hover:underline transition-all"
                        >
                            Click here to add a source
                        </button>
                    </div>
                ) : (
                    <div className="space-y-8">
                        <div className="flex items-center justify-between px-2">
                            <h3 className="font-bold text-slate-700 text-xl">All Documents</h3>
                            <span className="text-sm font-bold text-blue-600 px-4 py-1.5 bg-blue-50 rounded-full border border-blue-100">
                                {files.filter(f => f.checked).length} selected for context
                            </span>
                        </div>
                        <div className="flex flex-row items-center gap-4 px-4 py-2 border-b-2 border-slate-100 text-xs font-bold text-slate-400 uppercase tracking-wider ml-2">
                            <div className="w-6"></div>
                            <div className="flex-1">Name</div>
                            <div className="w-[150px] hidden sm:block">Date modified</div>
                            <div className="w-[100px] hidden md:block">Type</div>
                            <div className="w-[80px] hidden lg:block text-right pr-24">Size</div>
                        </div>

                        <div className="space-y-4">
                            {Object.entries(
                                files.reduce((acc, file) => {
                                    const parts = file.filename.split('/');
                                    const folder = parts.length > 1 ? parts.slice(0, -1).join('/') : "";
                                    if (!acc[folder]) acc[folder] = [];
                                    acc[folder].push(file);
                                    return acc;
                                }, {} as Record<string, typeof files>)
                            ).map(([folder, folderFiles]) => (
                                <div key={folder} className="space-y-1">
                                    <div 
                                        onClick={() => setExpandedFolders(prev => ({ ...prev, [folder]: prev[folder] === false ? true : false }))}
                                        className="flex items-center gap-3 cursor-pointer p-2 hover:bg-slate-100/80 rounded-xl w-full transition-all group select-none"
                                    >
                                        <ChevronDown className={cn("w-4 h-4 text-slate-400 transition-transform", expandedFolders[folder] === false ? "-rotate-90" : "")} />
                                        <div className="relative">
                                            <Folder className="w-5 h-5 text-blue-400 fill-blue-50" />
                                        </div>
                                        <span className="font-semibold text-slate-700 text-sm group-hover:text-blue-700 transition-colors">
                                            {folder === "" ? "Root Directory" : folder}
                                        </span>
                                        <span className="text-xs font-medium text-slate-400">
                                            {folderFiles.length} item{folderFiles.length !== 1 ? 's' : ''}
                                        </span>
                                    </div>

                                    <AnimatePresence initial={false}>
                                        {expandedFolders[folder] !== false && (
                                            <motion.div 
                                                initial={{ height: 0, opacity: 0 }}
                                                animate={{ height: "auto", opacity: 1 }}
                                                exit={{ height: 0, opacity: 0 }}
                                                className="overflow-hidden"
                                            >
                                                <div className="flex flex-col gap-2 pl-6 ml-[11px] border-l-2 border-slate-100 py-1">
                                        {folderFiles.map((file, idx) => {
                                            const fileColor = getFileColor(file.filename);
                                            const busy = isSummarizing === file.filename;
                                            const displayFilename = file.filename.split('/').pop() || file.filename;
                                            return (
                                                <motion.div
                                                    key={idx}
                                                    layout
                                                    initial={{ opacity: 0, y: 10 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    className="relative group w-full"
                                                >
                                                    <label
                                                        className={cn(
                                                            "flex flex-row items-center gap-4 p-2 rounded-xl transition-all cursor-pointer overflow-hidden w-full border border-transparent",
                                                            file.checked
                                                                ? "bg-blue-50/60 border-blue-100"
                                                                : "hover:bg-slate-50 hover:border-slate-200"
                                                        )}
                                                    >
                                                        {/* Checkbox */}
                                                        <div className="flex items-center justify-center pl-2">
                                                            <div className={cn("w-4 h-4 rounded border flex items-center justify-center transition-all", 
                                                                file.checked ? "border-blue-600 bg-blue-600" : "border-slate-300"
                                                            )}>
                                                                {file.checked && <CheckCircle2 className="w-3 h-3 text-white" />}
                                                            </div>
                                                        </div>

                                                        <input
                                                            type="checkbox"
                                                            checked={file.checked || false}
                                                            onChange={() => handleToggleFile(file.filename)}
                                                            className="hidden"
                                                        />

                                                        {/* Name Column */}
                                                        <div className="flex flex-1 items-center gap-3 min-w-[200px]">
                                                            <FileText className={cn("w-5 h-5", fileColor)} />
                                                            <span className="text-sm font-medium text-slate-700 truncate" title={displayFilename}>
                                                                {displayFilename}
                                                            </span>
                                                        </div>

                                                        {/* Date Modified Column */}
                                                        <div className="w-[150px] hidden sm:block text-xs text-slate-500 truncate" suppressHydrationWarning>
                                                            {file.updated ? new Date(file.updated).toLocaleDateString() + ' ' + new Date(file.updated).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '--'}
                                                        </div>

                                                        {/* Type Column */}
                                                        <div className="w-[100px] hidden md:block text-xs text-slate-500 truncate uppercase">
                                                            {displayFilename.split('.').pop()} File
                                                        </div>

                                                        {/* Size Column */}
                                                        <div className="w-[80px] hidden lg:block text-xs text-slate-500 text-right pr-4">
                                                            {file.size ? (file.size >= 1024 * 1024 ? (file.size / (1024 * 1024)).toFixed(1) + ' MB' : (file.size / 1024).toFixed(0) + ' KB') : '--'}
                                                        </div>

                                                        {/* Quick Actions - Always visible on hover, or static */}
                                                        <div className="opacity-0 group-hover:opacity-100 transition-all flex items-center gap-2 pr-2 shrink-0">
                                                            <button
                                                                onClick={(e) => { e.preventDefault(); e.stopPropagation(); setViewingFile(file.filename); }}
                                                                disabled={!!isSummarizing}
                                                                className="p-1.5 rounded-lg text-slate-400 hover:text-sky-600 hover:bg-sky-50 transition-all"
                                                                title="View"
                                                            >
                                                                <Eye className="w-4 h-4" />
                                                            </button>
                                                            <button
                                                                onClick={(e) => handleSummarizeFile(e, file.filename)}
                                                                disabled={!!isSummarizing}
                                                                className="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-all"
                                                                title="Summarize"
                                                            >
                                                                {busy ? <span className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin inline-block" /> : <Zap className="w-4 h-4" />}
                                                            </button>
                                                            <button
                                                                onClick={(e) => handleDeleteFile(e, file.filename)}
                                                                disabled={!!isSummarizing}
                                                                className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all"
                                                                title="Delete"
                                                            >
                                                                <Trash2 className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    </label>
                                                </motion.div>
                                            );
                                        })}
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Upload Modal */}
                <AnimatePresence>
                    {isUploadModalOpen && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md"
                            onClick={() => setIsUploadModalOpen(false)}
                        >
                            <motion.div
                                initial={{ scale: 0.9, opacity: 0, y: 30 }}
                                animate={{ scale: 1, opacity: 1, y: 0 }}
                                exit={{ scale: 0.9, opacity: 0, y: 30 }}
                                className="bg-white rounded-[2.5rem] shadow-2xl w-full max-w-lg overflow-hidden flex flex-col"
                                onClick={(e) => e.stopPropagation()}
                            >
                                <div className="p-8 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 rounded-2xl bg-blue-100 flex items-center justify-center text-blue-600 shadow-inner">
                                            <Plus className="w-6 h-6" />
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-bold text-slate-800">Add Source</h3>
                                            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Upload to Knowledge Base</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setIsUploadModalOpen(false)}
                                        className="p-3 hover:bg-white hover:shadow-md rounded-2xl transition-all"
                                    >
                                        <X className="w-6 h-6 text-slate-400" />
                                    </button>
                                </div>
                                
                                <div className="p-8 bg-white flex flex-col gap-6">
                                    {/* Folder Input */}
                                    <div className="flex flex-col gap-2">
                                        <label className="text-sm font-bold text-slate-700 ml-1">Folder Name (Optional)</label>
                                        <div className="relative">
                                            <div className="absolute left-4 top-1/2 -translate-y-1/2">
                                                <Folder className="w-5 h-5 text-slate-400" />
                                            </div>
                                            <input
                                                type="text"
                                                list="existing-folders"
                                                value={uploadFolder}
                                                onChange={(e) => setUploadFolder(e.target.value)}
                                                placeholder="e.g. finance, marketing, Q3-reports"
                                                className="w-full pl-12 pr-4 py-3 bg-slate-50 border-2 border-slate-200 rounded-2xl focus:outline-none focus:border-blue-500 focus:bg-white transition-all text-slate-700 font-medium"
                                            />
                                            <datalist id="existing-folders">
                                                {Array.from(new Set(files.map(f => {
                                                    const parts = f.filename.split('/');
                                                    return parts.length > 1 ? parts.slice(0, -1).join('/') : "";
                                                }).filter(f => f !== ""))).map(folder => (
                                                    <option key={folder} value={folder} />
                                                ))}
                                            </datalist>
                                        </div>
                                        <p className="text-xs text-slate-400 ml-1">Files will be placed in the root directory if left empty. You can also select existing folders.</p>
                                    </div>

                                    <div className="w-full h-px bg-slate-100 my-2"></div>

                                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                        <button
                                            onClick={() => docInputRef.current?.click()}
                                            className="flex flex-col items-center justify-center gap-3 p-4 rounded-2xl border-2 border-slate-200 bg-slate-50 hover:bg-blue-50 hover:border-blue-300 hover:shadow-md hover:shadow-blue-100 transition-all group"
                                        >
                                            <div className="w-12 h-12 bg-white rounded-xl shadow-sm border border-slate-200 flex items-center justify-center text-slate-600 group-hover:text-blue-600 group-hover:border-blue-300 transition-all">
                                                <FileText className="w-6 h-6" />
                                            </div>
                                            <span className="font-bold text-slate-700 group-hover:text-blue-700 text-sm">Document</span>
                                        </button>
                                        <button
                                            onClick={() => imgInputRef.current?.click()}
                                            className="flex flex-col items-center justify-center gap-3 p-4 rounded-2xl border-2 border-slate-200 bg-slate-50 hover:bg-amber-50 hover:border-amber-300 hover:shadow-md hover:shadow-amber-100 transition-all group"
                                        >
                                            <div className="w-12 h-12 bg-white rounded-xl shadow-sm border border-slate-200 flex items-center justify-center text-slate-600 group-hover:text-amber-600 group-hover:border-amber-300 transition-all">
                                                <FileImage className="w-6 h-6" />
                                            </div>
                                            <span className="font-bold text-slate-700 group-hover:text-amber-700 text-sm">Image</span>
                                        </button>
                                        <button
                                            onClick={() => audioInputRef.current?.click()}
                                            className="flex flex-col items-center justify-center gap-3 p-4 rounded-2xl border-2 border-slate-200 bg-slate-50 hover:bg-emerald-50 hover:border-emerald-300 hover:shadow-md hover:shadow-emerald-100 transition-all group"
                                        >
                                            <div className="w-12 h-12 bg-white rounded-xl shadow-sm border border-slate-200 flex items-center justify-center text-slate-600 group-hover:text-emerald-600 group-hover:border-emerald-300 transition-all">
                                                <FileAudio className="w-6 h-6" />
                                            </div>
                                            <span className="font-bold text-slate-700 group-hover:text-emerald-700 text-sm">Audio</span>
                                        </button>
                                    </div>
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Summary Modal */}
                <AnimatePresence>
                    {summary && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md"
                            onClick={() => setSummary(null)}
                        >
                            <motion.div
                                initial={{ scale: 0.9, opacity: 0, y: 30 }}
                                animate={{ scale: 1, opacity: 1, y: 0 }}
                                exit={{ scale: 0.9, opacity: 0, y: 30 }}
                                className="bg-white rounded-[2.5rem] shadow-2xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col"
                                onClick={(e) => e.stopPropagation()}
                            >
                                <div className="p-8 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
                                    <div className="flex items-center gap-4">
                                        <div className="w-14 h-14 rounded-2xl bg-blue-100 flex items-center justify-center text-blue-600 shadow-inner">
                                            <FileText className="w-7 h-7" />
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-bold text-slate-800">Document Analysis</h3>
                                            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">{summary.filename}</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setSummary(null)}
                                        className="p-3 hover:bg-white hover:shadow-md rounded-2xl transition-all"
                                    >
                                        <ChevronDown className="w-6 h-6 text-slate-400 rotate-180" />
                                    </button>
                                </div>
                                <div className="flex-1 overflow-y-auto p-10 bg-white">
                                    <div className="prose prose-slate prose-lg max-w-none text-slate-700 leading-relaxed italic-style-fix">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {summary.text}
                                        </ReactMarkdown>
                                    </div>
                                </div>
                                <div className="p-6 bg-slate-50/50 border-t border-slate-100 flex justify-end">
                                    <button
                                        onClick={() => setSummary(null)}
                                        className="px-8 py-3 bg-slate-900 text-white rounded-2xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg hover:shadow-slate-300"
                                    >
                                        Dismiss
                                    </button>
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* View File Modal */}
                <AnimatePresence>
                    {viewingFile && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md"
                            onClick={() => setViewingFile(null)}
                        >
                            <motion.div
                                initial={{ scale: 0.9, opacity: 0, y: 30 }}
                                animate={{ scale: 1, opacity: 1, y: 0 }}
                                exit={{ scale: 0.9, opacity: 0, y: 30 }}
                                className="bg-white rounded-[2.5rem] shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col"
                                onClick={(e) => e.stopPropagation()}
                            >
                                <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/80 shrink-0">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 rounded-2xl bg-sky-100 flex items-center justify-center text-sky-600 shadow-inner">
                                            <Eye className="w-6 h-6" />
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-bold text-slate-800">Preview</h3>
                                            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">{viewingFile}</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setViewingFile(null)}
                                        className="p-3 hover:bg-white hover:shadow-md rounded-2xl transition-all"
                                    >
                                        <X className="w-6 h-6 text-slate-400" />
                                    </button>
                                </div>
                                <div className="flex-1 overflow-y-auto bg-slate-100/50 p-6 flex flex-col items-center justify-center relative min-h-[50vh]">
                                    {(() => {
                                        const ext = viewingFile.split('.').pop()?.toLowerCase();
                                        const fileUrl = `http://localhost:8000/files/${encodeURIComponent(viewingFile)}/content`;
                                        if (['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(ext || '')) {
                                            return <img src={fileUrl} alt={viewingFile} className="max-w-full max-h-full object-contain rounded-xl shadow-sm border border-slate-200 bg-white" />;
                                        } else if (['mp3', 'wav', 'm4a'].includes(ext || '')) {
                                            return (
                                                <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-200 flex flex-col items-center gap-6 w-full max-w-md">
                                                    <div className="w-20 h-20 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center">
                                                        <FileAudio className="w-10 h-10" />
                                                    </div>
                                                    <audio src={fileUrl} controls className="w-full" autoPlay />
                                                </div>
                                            );
                                        } else {
                                            return <iframe src={fileUrl} className="w-full h-full min-h-[70vh] bg-white rounded-xl shadow-sm border border-slate-200" />;
                                        }
                                    })()}
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
