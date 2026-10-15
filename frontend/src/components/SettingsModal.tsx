import { useState, useEffect } from "react";
import { API_URL } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { X, Save, Key, Server, Thermometer } from "lucide-react";
import { AuthUser } from "@/lib/useAuth";

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    user: AuthUser;
}

export default function SettingsModal({ isOpen, onClose, user }: SettingsModalProps) {
    const [geminiKey, setGeminiKey] = useState("");
    const [groqKey, setGroqKey] = useState("");
    const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434/v1");
    const [temperature, setTemperature] = useState(0.3);
    
    const [isLoading, setIsLoading] = useState(false);
    const [isSaved, setIsSaved] = useState(false);

    useEffect(() => {
        if (isOpen) {
            // Load current settings from backend
            fetch(`${API_URL}/settings`, {
                headers: { "Authorization": `Bearer ${user.token}` }
            })
            .then(res => res.json())
            .then(data => {
                setGeminiKey(data.gemini_api_key || "");
                setGroqKey(data.groq_api_key || "");
                setOllamaUrl(data.ollama_url || "http://localhost:11434/v1");
                setTemperature(data.temperature ?? 0.3);
            })
            .catch(console.error);
        }
    }, [isOpen, user]);

    const handleSave = async () => {
        setIsLoading(true);
        try {
            await fetch(`${API_URL}/settings`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${user.token}` 
                },
                body: JSON.stringify({
                    gemini_api_key: geminiKey.includes("...") ? null : (geminiKey || null),
                    groq_api_key: groqKey.includes("...") ? null : (groqKey || null),
                    ollama_url: ollamaUrl,
                    temperature: temperature
                })
            });
            setIsSaved(true);
            setTimeout(() => {
                setIsSaved(false);
                onClose();
            }, 1000);
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                        onClick={onClose}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0, y: 10 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.95, opacity: 0, y: 10 }}
                            onClick={(e) => e.stopPropagation()}
                            className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col"
                        >
                            {/* Header */}
                            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                                <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
                                    <span className="p-1.5 bg-blue-100 text-blue-600 rounded-lg">
                                        <Key className="w-4 h-4" />
                                    </span>
                                    API Settings
                                </h2>
                                <button
                                    onClick={onClose}
                                    className="p-1.5 hover:bg-slate-200 rounded-full text-slate-500 transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>

                            {/* Body */}
                            <div className="p-5 space-y-5 flex-1 overflow-y-auto">
                                
                                {/* Temperature */}
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-slate-600 flex items-center justify-between">
                                        <span className="flex items-center gap-1.5">
                                            <Thermometer className="w-3.5 h-3.5" />
                                            System Temperature
                                        </span>
                                        <span className="text-blue-600 font-mono bg-blue-50 px-1.5 py-0.5 rounded">
                                            {temperature.toFixed(1)}
                                        </span>
                                    </label>
                                    <input 
                                        type="range" 
                                        min="0" max="1" step="0.1" 
                                        value={temperature}
                                        onChange={(e) => setTemperature(parseFloat(e.target.value))}
                                        className="w-full accent-blue-600"
                                    />
                                    <p className="text-[10px] text-slate-500 leading-tight">
                                        Lower values (0.1 - 0.3) make the AI more focused and deterministic. Higher values (0.7 - 1.0) make it more creative.
                                    </p>
                                </div>

                                {/* Gemini Key */}
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-slate-600">Gemini API Key</label>
                                    <input 
                                        type="password" 
                                        value={geminiKey}
                                        onChange={(e) => setGeminiKey(e.target.value)}
                                        placeholder="sk-..."
                                        className="w-full text-sm px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-mono"
                                    />
                                </div>

                                {/* Groq Key */}
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-slate-600">Groq API Key</label>
                                    <input 
                                        type="password" 
                                        value={groqKey}
                                        onChange={(e) => setGroqKey(e.target.value)}
                                        placeholder="gsk_..."
                                        className="w-full text-sm px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-mono"
                                    />
                                </div>

                                {/* Ollama URL */}
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-slate-600 flex items-center gap-1.5">
                                        <Server className="w-3.5 h-3.5" />
                                        Ollama Base URL
                                    </label>
                                    <input 
                                        type="text" 
                                        value={ollamaUrl}
                                        onChange={(e) => setOllamaUrl(e.target.value)}
                                        placeholder="http://localhost:11434/v1"
                                        className="w-full text-sm px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-mono"
                                    />
                                </div>

                            </div>

                            {/* Footer */}
                            <div className="px-5 py-4 border-t border-slate-100 bg-slate-50 flex justify-end">
                                <button
                                    onClick={handleSave}
                                    disabled={isLoading}
                                    className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-all active:scale-95 disabled:opacity-70"
                                >
                                    {isSaved ? <span className="animate-pulse">Saved!</span> : (
                                        <>
                                            <Save className="w-4 h-4" />
                                            {isLoading ? "Saving..." : "Save Settings"}
                                        </>
                                    )}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
