"use client";

import { useEffect, useState } from "react";
import {
    Activity,
    FileText,
    Zap,
    CheckCircle,
    Clock,
    DollarSign,
    RefreshCw
} from "lucide-react";
import { cn } from "@/lib/utils";

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Radar,
    Legend
} from "recharts";

interface DashboardMetrics {
    avg_retrieval_latency: number;
    avg_rerank_latency: number;
    avg_generation_latency: number;
    avg_bert_score: number;
    total_documents: number;
    total_cost: number;
    cost_available?: boolean;
    last_trace_at?: string | null;
    spans_sampled?: number;
    eval_date?: string | null;
    eval_samples?: number;
    ragas_metrics?: {
        faithfulness: number;
        answer_relevancy: number;
        context_precision: number;
        context_recall: number;
        semantic_accuracy: number;
    };
}

export default function Dashboard() {
    const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchMetrics = async () => {
        setLoading(true);
        setError(null);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const res = await fetch(`${apiUrl}/dashboard/metrics`);
            if (!res.ok) throw new Error("Failed to fetch metrics");
            const data = await res.json();
            setMetrics(data);
        } catch (err: any) {
            setError(err.message || "An error occurred");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMetrics();
    }, []);

    const MetricCard = ({ title, value, unit, icon: Icon, description, trend }: any) => (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-blue-50 to-blue-50/50 rounded-bl-full -mr-4 -mt-4 transition-transform group-hover:scale-110" />

            <div className="flex justify-between items-start mb-4 relative">
                <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl">
                    <Icon className="w-5 h-5" />
                </div>
            </div>

            <div className="relative">
                <h3 className="text-slate-500 text-sm font-medium mb-1">{title}</h3>
                <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-slate-800 tracking-tight">
                        {loading ? "-" : value}
                    </span>
                    {unit && <span className="text-slate-500 font-medium">{unit}</span>}
                </div>
                {description && (
                    <p className="text-xs text-slate-400 mt-2">{description}</p>
                )}
            </div>
        </div>
    );

    return (
        <div className="flex-1 flex flex-col h-full overflow-y-auto w-full">
            <div className="max-w-6xl mx-auto w-full p-8">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-800 tracking-tight">System Monitoring</h1>
                        <p className="text-slate-500 text-sm mt-1">Real-time performance and evaluation metrics</p>
                    </div>
                    <button
                        onClick={fetchMetrics}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-600 hover:text-blue-600 hover:border-blue-200 hover:bg-blue-50/50 transition-all disabled:opacity-50"
                    >
                        <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                        Refresh
                    </button>
                </div>

                {error ? (
                    <div className="p-4 bg-red-50 text-red-600 rounded-xl border border-red-100 text-sm">
                        Failed to load metrics: {error}
                    </div>
                ) : (
                    <div className="space-y-8">
                        {/* Primary Metrics Row */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            <MetricCard
                                title="RAGAS Score F1"
                                value={metrics?.avg_bert_score ? (metrics.avg_bert_score * 100).toFixed(1) : "0.0"}
                                unit="%"
                                icon={CheckCircle}
                                description={metrics?.eval_date
                                    ? `Last batch evaluation: ${metrics.eval_date} (${metrics.eval_samples ?? 0} samples). Target: >80%`
                                    : "No batch evaluation results found yet"}
                            />
                            <MetricCard
                                title="Total Estimated Cost"
                                value={metrics?.cost_available === false ? "n/a" : `$${metrics?.total_cost?.toFixed(4) || "0.0000"}`}
                                icon={DollarSign}
                                description={metrics?.cost_available === false
                                    ? "Token usage is not reported for streamed LLM calls"
                                    : "Estimated API usage cost based on input/output tokens"}
                            />
                            <MetricCard
                                title="Knowledge Base"
                                value={metrics?.total_documents || "0"}
                                unit="files"
                                icon={FileText}
                                description="Total number of documents currently indexed"
                            />
                        </div>

                        {/* Latency Section */}
                        <h2 className="text-lg font-semibold text-slate-800 mt-8 mb-4 flex items-center gap-2">
                            <Activity className="w-5 h-5 text-blue-500" />
                            Average Latency Breakdown
                        </h2>
                        <p className="text-xs text-slate-400 -mt-2">
                            {metrics?.last_trace_at
                                ? `From the latest ${metrics.spans_sampled ?? 0} Phoenix spans · last trace ${new Date(metrics.last_trace_at).toLocaleString()}`
                                : "No traces recorded yet"}
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <MetricCard
                                title="Retrieval Phase"
                                value={metrics?.avg_retrieval_latency ? (metrics.avg_retrieval_latency).toFixed(3) : "0.000"}
                                unit="s"
                                icon={Clock}
                                description="Average time to fetch chunks (seconds)"
                            />
                            <MetricCard
                                title="Reranker Phase"
                                value={metrics?.avg_rerank_latency ? (metrics.avg_rerank_latency).toFixed(3) : "0.000"}
                                unit="s"
                                icon={Clock}
                                description="Average time to rerank chunks (seconds)"
                            />
                            <MetricCard
                                title="Generation Phase"
                                value={metrics?.avg_generation_latency ? (metrics.avg_generation_latency).toFixed(2) : "0.00"}
                                unit="s"
                                icon={Zap}
                                description="Average LLM generation time (seconds)"
                            />
                        </div>

                        {/* RAGAS Evaluation Chart */}
                        <h2 className="text-lg font-semibold text-slate-800 mt-8 mb-4 flex items-center gap-2">
                            <CheckCircle className="w-5 h-5 text-emerald-500" />
                            RAGAS Quality Metrics Breakdown
                        </h2>

                        {metrics?.ragas_metrics && (
                            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
                                <div className="h-[350px] w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={[
                                            { subject: 'Faithfulness', A: metrics.ragas_metrics.faithfulness, fullMark: 1 },
                                            { subject: 'Relevancy', A: metrics.ragas_metrics.answer_relevancy, fullMark: 1 },
                                            { subject: 'Context Precision', A: metrics.ragas_metrics.context_precision, fullMark: 1 },
                                            { subject: 'Context Recall', A: metrics.ragas_metrics.context_recall, fullMark: 1 },
                                            { subject: 'Semantic Accuracy', A: metrics.ragas_metrics.semantic_accuracy, fullMark: 1 },
                                        ]}>
                                            <PolarGrid stroke="#e2e8f0" />
                                            <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 13 }} />
                                            <PolarRadiusAxis angle={30} domain={[0, 1]} tick={{ fill: '#94a3b8' }} />
                                            <Radar name="RAGAS Score" dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.4} />
                                            <Tooltip 
                                                formatter={(value) => [(Number(value ?? 0) * 100).toFixed(1) + '%', 'Score']}
                                                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)' }}
                                            />
                                        </RadarChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mt-6">
                                    {[
                                        { label: 'Faithfulness', value: metrics.ragas_metrics.faithfulness },
                                        { label: 'Relevancy', value: metrics.ragas_metrics.answer_relevancy },
                                        { label: 'Ctx Precision', value: metrics.ragas_metrics.context_precision },
                                        { label: 'Ctx Recall', value: metrics.ragas_metrics.context_recall },
                                        { label: 'Semantic Acc.', value: metrics.ragas_metrics.semantic_accuracy },
                                    ].map((item, idx) => (
                                        <div key={idx} className="text-center p-3 rounded-xl bg-slate-50 border border-slate-100">
                                            <div className="text-xs text-slate-500 font-medium mb-1">{item.label}</div>
                                            <div className="text-lg font-bold text-slate-800">{(item.value * 100).toFixed(1)}%</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
