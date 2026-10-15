import { useState } from "react";
import { API_URL } from "@/lib/utils";
import { Message, CitationSource } from "@/types/chat";
import { AuthUser } from "@/lib/useAuth";

type ChatMode = "fast" | "thinking" | "reasoning" | "deep_analytic";

interface UseChatStreamProps {
    user: AuthUser;
    currentSessionId: string | null;
    setCurrentSessionId: (id: string | null) => void;
    mode: ChatMode;
    selectedFiles: string[];
    fetchSessions: () => void;
    useOllama: boolean;
}

export function useChatStream({ user, currentSessionId, setCurrentSessionId, mode, selectedFiles, fetchSessions, useOllama }: UseChatStreamProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (input: string) => {
        if (!input.trim() || isLoading) return;

        const userMessage = input.trim();
        setMessages(prev => [
            ...prev,
            { role: "user", content: userMessage },
            {
                role: "assistant",
                content: "",
                mode,
                thinkingSteps: [],
                thinkingOpen: true, // Show animation tags for all modes (fast, reasoning, etc)
                isComplete: false,
            }
        ]);
        setIsLoading(true);

        try {
            const response = await fetch(`${API_URL}/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${user.token}`
                },
                body: JSON.stringify({
                    question: userMessage,
                    session_id: currentSessionId,
                    mode,
                    selected_files: selectedFiles,
                    use_ollama: useOllama
                }),
            });

            if (!response.ok) {
                let errorMsg = "Failed";
                try {
                    const errorData = await response.json();
                    if (errorData && errorData.detail) errorMsg = errorData.detail;
                } catch (e) {
                    console.error("Could not parse error response", e);
                }
                throw new Error(errorMsg);
            }
            if (!response.body) return;

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantMessage = "";
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split("\n\n");
                
                // Keep the last part in the buffer if it doesn't end with \n\n
                buffer = parts.pop() || "";

                for (const line of parts) {
                    // SSE comments (": ping" heartbeats) match no branch below and are ignored.
                    // ── session_id ────────────────────────────────────────────
                    if (line.startsWith("event: session_id")) {
                        const sid = line.replace("event: session_id\ndata: ", "").trim();
                        if (sid && sid !== currentSessionId) {
                            setCurrentSessionId(sid);
                            setTimeout(fetchSessions, 1000);
                        }

                    // ── thinking_step (reasoning / deep_analytic) ─────────────
                    } else if (line.startsWith("event: thinking_step")) {
                        try {
                            const parsed = JSON.parse(line.replace("event: thinking_step\ndata: ", ""));
                            setMessages(prev => {
                                const m = [...prev];
                                const last = m[m.length - 1];
                                if (last && last.role === "assistant") {
                                    last.thinkingSteps = [
                                        ...(last.thinkingSteps || []),
                                        { step: parsed.step, content: parsed.content }
                                    ];
                                    last.thinkingOpen = true;
                                }
                                return m;
                            });
                        } catch (err) {
                            console.error("thinking_step parse error:", err);
                        }

                    // ── context (legacy fast mode) ────────────────────────────
                    } else if (line.startsWith("event: context")) {
                        try {
                            const parsed = JSON.parse(line.replace("event: context\ndata: ", ""));
                            const ctxArray: string[] = Array.isArray(parsed?.contexts) ? parsed.contexts : [];
                            const metaArray: any[] = Array.isArray(parsed?.source_docs) ? parsed.source_docs : [];

                            const sources: CitationSource[] = ctxArray.map((content, i) => ({
                                filename: metaArray[i]?.source?.split(/[\\\/]/).pop() || "Unknown Document",
                                full_path: metaArray[i]?.source,
                                content,
                            }));

                            setMessages(prev => {
                                const m = [...prev];
                                m[m.length - 1].sources = sources;
                                return m;
                            });
                        } catch (err) {
                            console.error("Context parse error:", err);
                        }

                    // ── citation (all modes) ──────────────────────────────────
                    } else if (line.startsWith("event: citation")) {
                        try {
                            const parsed = JSON.parse(line.replace("event: citation\ndata: ", ""));
                            const sources: CitationSource[] = (parsed.sources || []).map((s: any) => ({
                                filename: s.filename || s.content || "Unknown",
                                full_path: s.full_path,
                                content: s.content,
                            }));
                            setMessages(prev => {
                                const m = [...prev];
                                const last = m[m.length - 1];
                                if (last && last.role === "assistant") {
                                    last.sources = sources;
                                }
                                return m;
                            });
                        } catch (err) {
                            console.error("Citation parse error:", err);
                        }

                    // ── token ─────────────────────────────────────────────────
                    } else if (line.startsWith("event: token")) {
                        try {
                            const token = JSON.parse(line.replace("event: token\ndata: ", ""));
                            assistantMessage += token;

                            const isStillThinking = assistantMessage.includes("<think>") && !assistantMessage.includes("</think>");
                            const displayMessage = assistantMessage
                                .replace(/<think>[\s\S]*?(?:<\/think>|$)/g, "")
                                .trimStart();

                            setMessages(prev => {
                                const m = [...prev];
                                const last = m[m.length - 1];
                                if (last && last.role === "assistant") {
                                    last.content = displayMessage;
                                    last.isThinking = isStillThinking;
                                    // Close thinking panel once answer starts arriving
                                    if (displayMessage.length > 0 && last.thinkingOpen) {
                                        last.thinkingOpen = false;
                                    }
                                }
                                return m;
                            });
                        } catch { }

                    // ── metrics ───────────────────────────────────────────────
                    } else if (line.startsWith("event: metrics")) {
                        try {
                            const metrics = JSON.parse(line.replace("event: metrics\ndata: ", ""));
                            setMessages(prev => {
                                const m = [...prev];
                                m[m.length - 1].metrics = metrics;
                                return m;
                            });
                        } catch { }

                    // ── chart_config ──────────────────────────────────────────
                    } else if (line.startsWith("event: chart_config")) {
                        try {
                            const config = JSON.parse(line.replace("event: chart_config\ndata: ", ""));
                            setMessages(prev => {
                                const m = [...prev];
                                const last = m[m.length - 1];
                                last.chartType = config.chart;
                                last.chartData = config.data;
                                return m;
                            });
                        } catch { }

                    // ── error (timeouts, pipeline failures) ───────────────────
                    } else if (line.startsWith("event: error")) {
                        let detail = "Sorry, something went wrong.";
                        try {
                            const parsed = JSON.parse(line.replace("event: error\ndata: ", ""));
                            if (parsed?.detail) detail = parsed.detail;
                        } catch { }
                        setMessages(prev => {
                            const m = [...prev];
                            const last = m[m.length - 1];
                            if (last && last.role === "assistant") {
                                last.content = last.content ? `${last.content}\n\n${detail}` : detail;
                                last.thinkingOpen = false;
                            }
                            return m;
                        });
                    }
                }
            }

            setMessages(prev => {
                const m = [...prev];
                m[m.length - 1].isComplete = true;
                m[m.length - 1].thinkingOpen = false; // Collapse thinking when done
                return m;
            });
            fetchSessions();

        } catch (error: any) {
            console.error(error);
            setMessages(prev => {
                const m = [...prev];
                const last = m[m.length - 1];
                if (last && last.role === "assistant") {
                    last.content = error.message || "Sorry, something went wrong.";
                    last.isComplete = true;
                    return m;
                }
                return [...prev, { role: "assistant", content: error.message || "Sorry, something went wrong.", isComplete: true }];
            });
        } finally {
            setIsLoading(false);
        }
    };

    return {
        messages,
        setMessages,
        isLoading,
        setIsLoading,
        handleSubmit
    };
}
