"use client";

import React from "react";
import {
    BookOpen, Info, Zap, Database, Activity,
    Layers, Cpu, ShieldCheck, ChevronRight,
    Search, Server, ArrowRight
} from "lucide-react";
import { motion } from "framer-motion";

export default function Documentation() {
    return (
        <div className="flex-1 flex flex-col h-full overflow-y-auto light-scrollbar">
            {/* Header */}
            <div className="px-8 py-10">
                <div className="max-w-4xl mx-auto">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="p-2 rounded-lg bg-blue-100 text-blue-600">
                            <BookOpen className="w-6 h-6" />
                        </div>
                        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Documentation</h1>
                    </div>
                    <p className="text-lg text-slate-600 leading-relaxed max-w-2xl">
                        Welcome to the Knowledge Inteligence Policy Technical Guide. This page provides a comprehensive overview of the system architecture,
                        the models powering our intelligence, and how we ensure quality through rigorous monitoring.
                    </p>
                </div>
            </div>

            <div className="max-w-4xl mx-auto py-12 px-8 space-y-16">

                {/* 1. App Overview */}
                <section>
                    <div className="flex items-center gap-2 mb-6">
                        <Info className="w-5 h-5 text-blue-500" />
                        <h2 className="text-xl font-bold text-slate-800 uppercase tracking-wider text-sm">Overview Aplikasi</h2>
                    </div>
                    <div className="bg-white rounded-2xl p-8 border border-slate-200 shadow-sm leading-relaxed text-slate-600 space-y-4">
                        <p>
                            <span className="font-semibold text-slate-800">Knowledge Inteligence Policy</span> adalah platform Document Intelligence yang dirancang khusus untuk membedah, menganalisis, dan mengekstrak informasi dari dokumen kebijakan teknis (Policy Documents).
                        </p>
                        <p>
                            Berbeda dengan Chatbot standar, aplikasi ini menggunakan arsitektur <span className="text-blue-600 font-medium font-mono text-xs bg-blue-50 px-1.5 py-0.5 rounded">Advanced RAG (Retrieval-Augmented Generation)</span> yang memastikan setiap jawaban didasarkan pada data faktual dari basis pengetahuan yang diunggah pengguna.
                        </p>
                    </div>
                </section>

                {/* 2. Chat Modes & Features */}
                <section>
                    <div className="flex items-center gap-2 mb-6">
                        <Zap className="w-5 h-5 text-amber-500" />
                        <h2 className="text-xl font-bold text-slate-800 uppercase tracking-wider text-sm">Fitur & Mode Chat</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
                            <h3 className="text-md font-bold text-slate-800 mb-3 flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                                Fast Mode (Llama 3.3)
                            </h3>
                            <p className="text-sm text-slate-600 leading-relaxed">
                                Dioptimalkan untuk kecepatan. Menggunakan model <span className="font-medium text-slate-800">Llama 3.3 70B</span> untuk memberikan jawaban cepat dan ringkas berdasarkan dokumen yang relevan.
                            </p>
                        </div>
                        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
                            <h3 className="text-md font-bold text-slate-800 mb-3 flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-sky-500" />
                                Deep Mode (Qwen 3 32B)
                            </h3>
                            <p className="text-sm text-slate-600 leading-relaxed">
                                Mode penalaran mendalam. Menggunakan <span className="font-medium text-slate-800">Qwen 3 32B Reasoning</span> untuk membedah instruksi kompleks, melakukan perbandingan antar dokumen, dan memberikan analisis terperinci.
                            </p>
                        </div>
                    </div>
                </section>

                {/* 3. Model Stack & Tech */}
                <section>
                    <div className="flex items-center gap-2 mb-6">
                        <Cpu className="w-5 h-5 text-blue-500" />
                        <h2 className="text-xl font-bold text-slate-800 uppercase tracking-wider text-sm">Intelligence Stack</h2>
                    </div>
                    <div className="bg-blue-950 rounded-2xl p-8 border border-white/10 shadow-xl overflow-hidden relative">
                        {/* Decorative background element */}
                        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 blur-3xl rounded-full translate-x-1/2 -translate-y-1/2" />

                        <div className="space-y-8 relative z-10 text-slate-300">
                            <div className="flex gap-6 items-start">
                                <div className="mt-1 p-2 rounded-lg bg-blue-900 text-blue-400">
                                    <Layers className="w-5 h-5" />
                                </div>
                                <div>
                                    <h4 className="text-white font-bold mb-1">Vector Database & Embeddings</h4>
                                    <p className="text-sm">
                                        Menggunakan <span className="text-blue-400 font-medium">Weaviate</span> sebagai mesin pencari vektor. Teks dikonversi menjadi representasi numerik menggunakan model <span className="text-blue-400 font-medium">BGE-Base-ID</span> yang spesifik dioptimalkan untuk Bahasa Indonesia.
                                    </p>
                                </div>
                            </div>

                            <div className="flex gap-6 items-start">
                                <div className="mt-1 p-2 rounded-lg bg-blue-900 text-cyan-400">
                                    <Search className="w-5 h-5" />
                                </div>
                                <div>
                                    <h4 className="text-white font-bold mb-1">Hybrid Search & Reranking</h4>
                                    <p className="text-sm">
                                        Pencarian dilakukan dalam dua tahap: Keyword search (BM25) dan Vector search. Hasil mentah kemudian diperingkat ulang menggunakan <span className="text-cyan-400 font-medium">BGE Reranker-v2-m3</span> untuk presisi maksimal.
                                    </p>
                                </div>
                            </div>

                            <div className="flex gap-6 items-start">
                                <div className="mt-1 p-2 rounded-lg bg-blue-900 text-emerald-400">
                                    <Server className="w-5 h-5" />
                                </div>
                                <div>
                                    <h4 className="text-white font-bold mb-1">Inference Engine</h4>
                                    <p className="text-sm">
                                        Ditenagai oleh <span className="text-emerald-400 font-medium">Groq LPU (Language Processing Unit)</span> untuk latensi minimal (sub-second streaming) dan keandalan tinggi.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* 4. Document Pipeline */}
                <section>
                    <div className="flex items-center gap-2 mb-6">
                        <Database className="w-5 h-5 text-emerald-500" />
                        <h2 className="text-xl font-bold text-slate-800 uppercase tracking-wider text-sm">Data Pipeline RAG</h2>
                    </div>
                    <div className="relative">
                        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-slate-200" />

                        <div className="space-y-10 pl-16">
                            {[
                                { title: "Loading & Extraction", desc: "Dokumen (PDF/Word/Images) dibedah menggunakan Docling untuk mengekstrak struktur Markdown yang bersih." },
                                { title: "Semantic Splitting", desc: "Teks dipotong berdasarkan Heading Markdown untuk menjaga keutuhan konteks informasi (Heading-aware Chunking)." },
                                { title: "Vector Indexing", desc: "Teks dikonversi menjadi vektor dan disimpan di Weaviate bersama metadata dokumen aslinya." },
                                { title: "Retrieval & Rerank", desc: "Sistem mengambil konteks paling relevan dan melakukan scoring ulang sebelum dikirim ke LLM." },
                                { title: "Grounded Generation and Guardrails", desc: "LLM menjawab pertanyaan pengguna HANYA berdasarkan konteks yang ditemukan (Grounding) untuk mencegah halusinasi." },
                            ].map((step, i) => (
                                <div key={i} className="relative">
                                    <div className="absolute -left-16 top-1.5 w-8 h-8 rounded-full bg-white border-2 border-slate-200 flex items-center justify-center z-10 shadow-sm">
                                        <span className="text-xs font-bold text-slate-400">{i + 1}</span>
                                    </div>
                                    <h4 className="font-bold text-slate-800 mb-1">{step.title}</h4>
                                    <p className="text-sm text-slate-500 italic max-w-lg">{step.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* 5. Monitoring & Evaluation */}
                <section>
                    <div className="flex items-center gap-2 mb-6">
                        <Activity className="w-5 h-5 text-blue-500" />
                        <h2 className="text-xl font-bold text-slate-800 uppercase tracking-wider text-sm">Monitoring & Evaluasi</h2>
                    </div>
                    <div className="bg-slate-900 rounded-2xl p-8 border border-white/5 shadow-2xl">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                            <div>
                                <h3 className="text-blue-400 font-bold mb-4 flex items-center gap-2">
                                    <Zap className="w-4 h-4" />
                                    Arize Phoenix
                                </h3>
                                <p className="text-sm text-slate-400 leading-relaxed">
                                    Tracing real-time untuk setiap query. Kami melacak latensi setiap tahap (Retriever, Reranker, LLM) dan visualisasi vector space untuk debugging kualitas pencarian.
                                </p>
                            </div>
                            <div>
                                <h3 className="text-emerald-400 font-bold mb-4 flex items-center gap-2">
                                    <ShieldCheck className="w-4 h-4" />
                                    RAGAS Evaluation
                                </h3>
                                <p className="text-sm text-slate-400 leading-relaxed">
                                    Sistem evaluasi menggunakan <span className="font-medium text-slate-300">RAGAS</span>. Kami memantau <span className="font-medium text-slate-300">Faithfulness</span> (kejujuran model) dan <span className="font-medium text-slate-300">BERT Score</span> untuk kualitas jawaban.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>

                <div className="pt-10 border-t border-slate-200">
                    <p className="text-center text-xs text-slate-400 font-medium">
                        Knowledfe Inteligence Policy &copy; 2026 • Document Intelligence Engine v2.4.0
                    </p>
                </div>
            </div>
        </div>
    );
}
