"use client";

import { useState, useRef, useEffect } from "react";
import { Upload, FileSpreadsheet, Activity, Bot, ChevronRight, BarChart2, PieChart, Info, CheckCircle2, Database, Clock, FileText } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { AuthUser } from "@/lib/useAuth";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { DataAnalysisCharts } from "./DataAnalysisCharts";

interface DataAnalysisViewProps {
  user: AuthUser;
}

export default function DataAnalysisView({ user }: DataAnalysisViewProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [bqTables, setBqTables] = useState<{dataset: string, table: string, id: string}[]>([]);
  const [selectedBqTable, setSelectedBqTable] = useState<string>("");
  const [historyList, setHistoryList] = useState<{id: string, title: string, timestamp: string}[]>([]);

  useEffect(() => {
    const fetchBqTables = async () => {
      try {
        const response = await fetch("http://localhost:8000/data-analysis/bigquery/tables", {
          headers: { "Authorization": `Bearer ${user.token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setBqTables(data);
        }
      } catch (err) {
        console.error("Failed to fetch BigQuery tables:", err);
      }
    };
    
    const fetchHistory = async () => {
      try {
        const response = await fetch("http://localhost:8000/data-analysis/history", {
          headers: { "Authorization": `Bearer ${user.token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setHistoryList(data);
        }
      } catch (err) {
        console.error("Failed to fetch history:", err);
      }
    };

    fetchBqTables();
    fetchHistory();
  }, [user.token]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelection(e.target.files[0]);
    }
  };

  const handleFileSelection = (selectedFile: File) => {
    const validExtensions = ['.csv', '.xls', '.xlsx'];
    const fileExtension = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
    
    if (!validExtensions.includes(fileExtension)) {
      setError("Please upload a valid .csv, .xls, or .xlsx file.");
      return;
    }
    
    setError(null);
    setFile(selectedFile);
    uploadAndAnalyze(selectedFile);
  };

  const uploadAndAnalyze = async (fileToUpload: File) => {
    setIsAnalyzing(true);
    setResult(null);
    setError(null);

    const formData = new FormData();
    formData.append("file", fileToUpload);

    try {
      const response = await fetch("http://localhost:8000/data-analysis/upload", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${user.token}`
        },
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Analysis failed");
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "An error occurred during analysis.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const analyzeBigQuery = async () => {
    if (!selectedBqTable) return;
    
    setIsAnalyzing(true);
    setResult(null);
    setError(null);
    
    const [dataset_id, table_id] = selectedBqTable.split(".");

    try {
      const response = await fetch("http://localhost:8000/data-analysis/bigquery/analyze", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${user.token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ dataset_id, table_id }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Analysis failed");
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "An error occurred during BigQuery analysis.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const loadHistoryItem = async (id: string) => {
    setIsAnalyzing(true);
    setResult(null);
    setError(null);
    try {
      const response = await fetch(`http://localhost:8000/data-analysis/history/${id}`, {
        headers: { "Authorization": `Bearer ${user.token}` }
      });
      if (!response.ok) throw new Error("Gagal memuat riwayat");
      const data = await response.json();
      setResult(data.result);
      setFile(new File([], data.title));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden w-full relative z-10 bg-slate-50">
      {/* History Sidebar */}
      <div className="w-72 border-r border-slate-200 bg-white flex flex-col h-full hidden md:flex">
        <div className="p-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-800 flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-500" />
            Riwayat Analisis
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
                <div className="bg-sky-100 p-2 rounded-lg text-sky-600 mt-0.5">
                  <FileText className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-700 truncate w-44">{item.title}</p>
                  <p className="text-xs text-slate-400 mt-1">{new Date(item.timestamp).toLocaleDateString()}</p>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto light-scrollbar p-6 lg:p-10">
      
      {/* Header Area */}
      <div className="max-w-6xl mx-auto mb-10 text-center">
        <div className="inline-flex items-center justify-center p-3 bg-gradient-to-br from-sky-500 to-blue-600 rounded-2xl shadow-lg shadow-sky-500/20 mb-4">
          <Activity className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Smart Data Analysis</h1>
        <p className="text-slate-500 text-sm max-w-lg mx-auto">
          Upload your Excel or CSV files. Our AI will automatically analyze the dataset, generate statistical insights, and create visual charts.
        </p>
      </div>

      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Top Chatbot Input */}
        <div className="bg-white rounded-2xl p-2 shadow-sm border border-slate-200 flex items-center relative z-20">
          <input 
            type="text" 
            placeholder={result ? "Tanyakan sesuatu tentang analisis ini..." : "Upload data terlebih dahulu untuk mulai bertanya..."}
            disabled={!result}
            className="flex-1 bg-transparent px-4 py-3 outline-none text-sm text-slate-700 disabled:opacity-50"
          />
          <button 
            disabled={!result}
            className="p-3 bg-sky-600 text-white rounded-xl hover:bg-sky-700 disabled:bg-slate-200 disabled:text-slate-400 transition-colors"
          >
            <Bot className="w-5 h-5" />
          </button>
        </div>

        {/* Input Zones */}
        {!result && !isAnalyzing && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={`border-2 border-dashed rounded-3xl p-12 text-center transition-all cursor-pointer bg-white ${
                isDragging ? "border-sky-500 bg-sky-50/50 scale-[1.02]" : "border-slate-200 hover:border-sky-300 hover:bg-slate-50"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".csv,.xls,.xlsx"
                onChange={handleFileInput}
              />
              <div className="w-20 h-20 mx-auto bg-sky-100 text-sky-600 rounded-full flex items-center justify-center mb-6">
                <Upload className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Upload dataset Anda</h3>
              <p className="text-slate-500 text-sm mb-6">Tarik dan lepas file Excel/CSV di sini, atau klik untuk memilih</p>
              <div className="flex items-center justify-center gap-4 text-xs font-medium text-slate-400">
                <span className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg"><FileSpreadsheet className="w-4 h-4 text-emerald-500" /> .CSV</span>
                <span className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg"><FileSpreadsheet className="w-4 h-4 text-emerald-500" /> .XLSX</span>
              </div>
              
              {error && (
                <div className="mt-6 p-4 bg-red-50 text-red-600 rounded-xl text-sm border border-red-100 flex items-center justify-center gap-2">
                  <Info className="w-4 h-4" />
                  {error}
                </div>
              )}
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="border-2 border-slate-200 rounded-3xl p-12 text-center bg-white"
            >
              <div className="w-20 h-20 mx-auto bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-6">
                <Database className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Pilih Data Table</h3>
              <p className="text-slate-500 text-sm mb-6">Analisis langsung dari tabel BigQuery yang tersedia</p>
              
              <div className="flex flex-col gap-4 max-w-xs mx-auto">
                <select 
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none text-sm text-slate-700"
                  value={selectedBqTable}
                  onChange={(e) => setSelectedBqTable(e.target.value)}
                >
                  <option value="">-- Pilih Tabel BigQuery --</option>
                  {bqTables.map(table => (
                    <option key={table.id} value={table.id}>{table.dataset}.{table.table}</option>
                  ))}
                </select>
                
                <button 
                  disabled={!selectedBqTable}
                  onClick={analyzeBigQuery}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Analisis Tabel
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Loading State */}
        {isAnalyzing && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="bg-white rounded-3xl p-12 shadow-sm border border-slate-200 text-center flex flex-col items-center justify-center min-h-[400px]"
          >
            <div className="relative w-24 h-24 mb-8">
              <div className="absolute inset-0 border-4 border-slate-100 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-sky-500 rounded-full border-t-transparent animate-spin"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <Bot className="w-8 h-8 text-sky-500 animate-pulse" />
              </div>
            </div>
            <h3 className="text-lg font-bold text-slate-800 mb-2">Menganalisis dataset Anda...</h3>
            <p className="text-slate-500 text-sm">AI sedang menghitung statistik dan menghasilkan 5 pertanyaan analisis komprehensif beserta chartnya.</p>
            
            <div className="mt-8 flex flex-col gap-3 w-64 mx-auto text-left">
              <div className="flex items-center gap-3 text-sm font-medium text-slate-400 animate-pulse">
                 <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Membaca struktur file
              </div>
              <div className="flex items-center gap-3 text-sm font-medium text-slate-400 animate-pulse" style={{ animationDelay: '0.5s' }}>
                 <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Menghitung statistik & insight
              </div>
              <div className="flex items-center gap-3 text-sm font-medium text-slate-400 animate-pulse" style={{ animationDelay: '1s' }}>
                 <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Menghasilkan 5 analisis mendalam
              </div>
            </div>
          </motion.div>
        )}

        {/* Results Area */}
        {result && !isAnalyzing && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} 
            className="space-y-6 pb-20"
          >
            <div className="flex items-center justify-between bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center">
                  <FileSpreadsheet className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-800">{file?.name}</h2>
                  <p className="text-xs text-slate-500 font-medium" suppressHydrationWarning>Analisis Selesai • {new Date().toLocaleTimeString()}</p>
                </div>
              </div>
              <button 
                onClick={() => { setResult(null); setFile(null); }}
                className="px-4 py-2 bg-slate-100 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-200 transition-colors shadow-sm"
              >
                Upload File Lain
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Narrative & Stats */}
              <div className="lg:col-span-1 flex flex-col gap-6">
                
                {/* Narrative Card */}
                <div className="bg-gradient-to-br from-sky-600 to-blue-700 rounded-3xl p-6 shadow-lg relative overflow-hidden text-white">
                  <div className="flex items-center gap-2 mb-4">
                    <Bot className="w-5 h-5 text-sky-200" />
                    <h3 className="font-bold text-white">Executive Summary</h3>
                  </div>
                  <div className="prose prose-invert prose-sm max-w-none text-slate-100 leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {result.narration || "Tidak ada narasi."}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Stats Card */}
                <div className="bg-white rounded-3xl p-6 shadow-sm border border-slate-200">
                  <div className="flex items-center gap-2 mb-4">
                    <BarChart2 className="w-5 h-5 text-sky-500" />
                    <h3 className="font-bold text-slate-800">Highlight Statistik</h3>
                  </div>
                  <div className="prose prose-slate prose-sm max-w-none text-slate-600 leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {result.statistical_summary || "Tidak ada ringkasan statistik."}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>

              {/* Right Column: 5 Analyses */}
              <div className="lg:col-span-2 flex flex-col gap-6">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-slate-800 text-lg">5 Analisis Mendalam</h3>
                  <div className="flex-1 h-px bg-slate-200 ml-4"></div>
                </div>

                {result.analyses && result.analyses.map((analysis: any, idx: number) => (
                  <div key={idx} className="bg-white rounded-3xl p-6 shadow-sm border border-slate-200 overflow-hidden relative">
                    <div className="absolute top-0 left-0 w-1.5 h-full bg-sky-400"></div>
                    <div className="flex items-start gap-4 mb-6">
                      <div className="w-8 h-8 rounded-full bg-sky-100 text-sky-600 font-bold flex items-center justify-center shrink-0">
                        {idx + 1}
                      </div>
                      <div>
                        <h4 className="text-lg font-bold text-slate-800">{analysis.question}</h4>
                        <div className="prose prose-slate prose-sm max-w-none text-slate-600 mt-2 leading-relaxed">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {analysis.answer}
                          </ReactMarkdown>
                        </div>
                      </div>
                    </div>
                    
                    {analysis.chart && (
                      <div className="mt-4 border-t border-slate-100 pt-6">
                        <DataAnalysisCharts config={analysis.chart} />
                      </div>
                    )}
                  </div>
                ))}
                
              </div>
            </div>
          </motion.div>
        )}
      </div>
      </div>
    </div>
  );
}
