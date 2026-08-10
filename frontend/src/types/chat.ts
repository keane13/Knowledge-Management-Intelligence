export interface ThinkingStep {
    step: string;
    content: string;
}

export interface CitationSource {
    filename: string;
    full_path?: string;
    content?: string;
}

export interface Message {
    role: 'user' | 'assistant';
    content: string;
    imagePreview?: string;
    isThinking?: boolean;
    isComplete?: boolean;
    mode?: string;
    thinkingSteps?: ThinkingStep[];
    thinkingOpen?: boolean;
    metrics?: {
        latency: number;
        faithfulness?: number;
        answer_relevancy?: number;
    };
    sources?: CitationSource[];
    chartType?: string;
    chartData?: any[];
}

export interface Session {
    id: string;
    title: string;
    timestamp: string;
}

export interface FileItem {
    filename: string;
    checked?: boolean;
    size?: number;
    updated?: string;
}

export interface RetrievalContext {
    page_content: string;
    metadata: Record<string, any>;
}
