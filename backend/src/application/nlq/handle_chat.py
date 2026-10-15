import os, re, json, time, logging
from typing import Dict, Any, AsyncGenerator

from google.adk.runners import Runner
from google.adk.events import Event
from google.adk.agents import LlmAgent, SequentialAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.genai.types import (
    GenerateContentConfig, ToolConfig, FunctionCallingConfig, Content, Part
)
from src.domain.agents.nlq_agent.prompts import SEARCH_AGENT_PROMPT
from src.infrastructure.tools.mcp_toolbox import toolset
from src.infrastructure.persistence.semantic_cache import get_semantic_match, set_semantic_cache
from src.application.services.input_validator import validate_input
from src.infrastructure.llm.timeouts import (
    NLQ_TIMEOUT_S, adk_http_options, is_timeout_error, iterate_with_deadline
)
from semantic_router import Route, SemanticRouter
from semantic_router.encoders import HuggingFaceEncoder, LiteLLMEncoder
from langsmith import traceable


# ─── INTENT ROUTING ──────────────────────────────────────────────────────────
# Multilingual encoder because users ask in Indonesian. It has the same 384 dimensions as the
# old all-MiniLM-L6-v2, so the Firestore vector index of the semantic cache still fits.
ENCODER_MODEL = os.getenv(
    "SEMANTIC_ENCODER_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
# Minimum route similarity; below it we fall back to the keyword rules.
# 0.5 scored 31/32 on a labeled set of Indonesian KB / data / greeting questions (0.6: 28/32).
ROUTE_SCORE_THRESHOLD = float(os.getenv("ROUTE_SCORE_THRESHOLD", "0.5"))

# The Knowledge Base holds Indonesian regulations: any of these words means "use RAG".
_REGULATION_WORDS = {
    "uu", "undang", "undang-undang", "perpres", "pp", "permen", "perda", "perppu", "keppres",
    "inpres", "pasal", "ayat", "peraturan", "regulasi", "ketentuan", "sanksi", "pidana",
}
# Keyword fallback for data questions: needs a quantity word AND a BigQuery domain term
# (datasets: finance, hr, legal, marketing — see domain/agents/nlq_agent/prompts.py).
_QUANTITY_WORDS = {
    "berapa", "jumlah", "total", "rata-rata", "average", "hitung", "count", "sum",
    "tertinggi", "terendah", "terbesar", "terkecil", "terbanyak", "top", "bottom",
    "bandingkan", "compare", "breakdown", "distribusi", "distribution", "persentase",
    "tren", "trend", "ranking", "tampilkan", "show", "list", "daftar", "highest", "lowest",
}
_DATA_DOMAIN_WORDS = {
    "budget", "budgets", "anggaran", "invoice", "invoices", "faktur", "tagihan",
    "pendapatan", "revenue", "profit", "laba", "profitabilitas", "expense", "expenses",
    "pengeluaran", "biaya", "reimburse", "karyawan", "pegawai", "employee", "employees",
    "gaji", "salary", "kompensasi", "compensation", "departemen", "department", "rekrutmen",
    "recruitment", "kandidat", "pelatihan", "training", "kinerja", "performance",
    "kampanye", "campaign", "campaigns", "klien", "client", "clients", "customer",
    "pelanggan", "opportunity", "opportunities", "pipeline", "kompetitor", "competitor",
    "kontrak", "contract", "contracts", "nda", "ndas", "roi", "leads", "penjualan", "sales",
    "proyek", "project",
}
_GREETING_WORDS = {"halo", "hai", "hello", "hi", "hey", "thanks", "makasih", "terima", "selamat", "pagi", "siang", "sore", "malam"}

# ─── ENCODERS & ROUTERS ─────────────────────────────────────────────────────────

_hf_encoder = None

def get_hf_encoder():
    global _hf_encoder
    if _hf_encoder is None:
        _hf_encoder = HuggingFaceEncoder(name=ENCODER_MODEL, score_threshold=ROUTE_SCORE_THRESHOLD)
    return _hf_encoder

def get_gemini_encoder():
    # Name kept for existing callers; the semantic cache shares the local HuggingFace encoder.
    return get_hf_encoder()

_router_hf = None

def _get_routes():
    return [
        Route(
            name="Greeting",
            utterances=[
                "halo", "hai", "hello", "hi", "selamat pagi",
                "siapa kamu", "apa kabar", "terima kasih", "thanks",
                "help", "bantuan", "apa yang bisa kamu lakukan",
            ]
        ),
        Route(
            name="Data Query",
            utterances=[
                "berapa total budget per departemen", "tampilkan 5 invoice dengan nilai terbesar",
                "berapa total pengeluaran expense report bulan ini", "profitabilitas proyek tertinggi",
                "berapa jumlah karyawan per departemen", "rata-rata gaji karyawan",
                "status rekrutmen kandidat", "hasil performance review karyawan",
                "kampanye marketing dengan ROI tertinggi", "daftar klien dan nilai opportunity",
                "berapa nilai pipeline penjualan", "kontrak yang akan berakhir tahun ini",
                "how many employees per department", "revenue breakdown by client",
                "top 5 customers by revenue", "compare planned vs actual budget",
            ]
        ),
        Route(
            name="Knowledge Base",
            utterances=[
                "apa tujuan undang-undang tentang pengelolaan zakat",
                "jelaskan isi peraturan presiden tentang", "apa yang diatur dalam pasal",
                "siapa yang berwenang menetapkan peraturan", "apa sanksi bagi pelanggar menurut undang-undang",
                "berapa lama masa jabatan anggota badan", "apa definisi pemajuan kebudayaan",
                "jelaskan tugas dan fungsi lembaga", "apa kewajiban pemerintah daerah menurut peraturan",
                "rangkum dokumen kebijakan ini", "apa isi dokumen yang saya unggah",
                "what does the regulation say about", "summarize this policy document",
            ]
        ),
    ]

def get_semantic_router_hf():
    global _router_hf
    if _router_hf is None:
        _router_hf = SemanticRouter(encoder=get_hf_encoder(), routes=_get_routes(), auto_sync="local")
    return _router_hf

def get_semantic_router_gemini():
    return get_semantic_router_hf()

def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower()))

@traceable(name="intent_detection")
def _detect_intent(text: str) -> str:
    words = _words(text)

    # Questions about laws/regulations always go to the document Knowledge Base
    if words & _REGULATION_WORDS:
        return "Knowledge Base"

    start_hf = time.time()
    try:
        route_hf = get_semantic_router_hf()(text)
    except Exception as e:
        logging.warning(f"HF Semantic router failed: {e}")
        route_hf = None
    latency_hf = int((time.time() - start_hf) * 1000)
    logging.info(f"[Router Latency] HuggingFace: {latency_hf}ms")

    route_name = route_hf.name if route_hf else None
    if route_name in ("Data Query", "Greeting", "Knowledge Base"):
        return route_name

    # Router unsure: whole-word keyword rules
    if words & _QUANTITY_WORDS and words & _DATA_DOMAIN_WORDS:
        return "Data Query"
    if words & _GREETING_WORDS and len(words) <= 4:
        return "Greeting"
    return "Knowledge Base"


# ─── CHART AGENT (deterministic — no LLM) ────────────────────────────────────
class ChartAgent(BaseAgent):
    name: str = "ChartAgent"
    description: str = "Deterministic chart type selection. No LLM."

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from google.adk.events.event_actions import EventActions
        data_json_str = ctx.session.state.get("sql_data_result", "")
        if data_json_str:
            ct = self._determine_chart_type(data_json_str)
            if ct != "NO_CHART_NEEDED":
                try:
                    yield Event(actions=EventActions(state_delta={
                        "chart_ready": True,
                        "chart_type": ct,
                        "chart_data": json.loads(data_json_str)
                    }))
                except Exception:
                    pass
        yield Event()

    def _determine_chart_type(self, data_json_str: str) -> str:
        try:
            data = json.loads(data_json_str)
            if not data or not isinstance(data, list): return "NO_CHART_NEEDED"
            r = data[0]
            if not isinstance(r, dict) or len(r) < 2: return "NO_CHART_NEEDED"
            has_str = any(isinstance(v, str) for v in r.values())
            has_num = any(isinstance(v, (int, float)) for v in r.values())
            if has_str and has_num:
                return "Bar Chart" if len(data) < 15 else "Line Chart"
            elif sum(isinstance(v, (int, float)) for v in r.values()) >= 2:
                return "Line Chart"
            return "NO_CHART_NEEDED"
        except Exception:
            return "NO_CHART_NEEDED"


# ─── GENERATOR AGENT ─────────────────────────────────────────────────────────
def get_generator_agent(model_name: str, for_greeting: bool = False) -> LlmAgent:
    instruction = "You are a professional AI Assistant.\n"
    if for_greeting:
        instruction += "Generate a friendly and helpful conversational response."
    else:
        instruction += (
            "**Data:** {{sql_data_result}}\n\n"
            "Synthesize into a comprehensive Markdown response in Indonesian language. "
            "Use Markdown tables for tabular data. Highlight key insights."
        )
    return LlmAgent(
        name="GeneratorAgent", model=model_name,
        instruction=instruction,
        description="Formats SQL data into natural language.",
        output_key="final_response",
        generate_content_config=GenerateContentConfig(http_options=adk_http_options())
    )


# ─── MAIN USE CASE ───────────────────────────────────────────────────────────
class HandleChatUseCase:
    def __init__(self, persistence_service, model_name: str = "gemini-flash-lite-latest"):
        self.persistence = persistence_service
        self.model_name = model_name

        self.search_agent = LlmAgent(
            name="SearchDataAgent", model=self.model_name,
            instruction=SEARCH_AGENT_PROMPT,
            description="Queries BigQuery via MCP Toolbox, returns raw JSON.",
            tools=[toolset], output_key="sql_data_result",
            generate_content_config=GenerateContentConfig(
                tool_config=ToolConfig(
                    function_calling_config=FunctionCallingConfig(mode="AUTO")
                ),
                http_options=adk_http_options()
            )
        )
        self.chart_agent = ChartAgent()
        self.data_pipeline = SequentialAgent(
            name="DataPipelineAgent",
            sub_agents=[self.search_agent, self.chart_agent, get_generator_agent(self.model_name, False)],
            description="NLQ pipeline: query -> chart -> narration."
        )
        self.greeting_pipeline = SequentialAgent(
            name="GreetingPipelineAgent",
            sub_agents=[get_generator_agent(self.model_name, True)],
            description="Fast path for greetings."
        )

    @traceable(name="execute_chat_use_case")
    async def execute(
        self, session_id: str, user_id: str, message: str
    ) -> AsyncGenerator[Dict[str, Any], None]:

        # 1. Input guardrail
        if not validate_input(message):
            yield {"type": "chunk", "content": "Input tidak dapat diproses."}
            return

        start_time = time.time()
        intent = "Data Query"  # Forcing Data Query since we route using _detect_intent beforehand

        if intent == "Data Query":
            # 2. Semantic cache (using Gemini encoder as primary)
            cached = get_semantic_match(message, encoder=get_gemini_encoder(), namespace="nlq")
            if cached:
                import asyncio
                words = cached.get("content", "").split(" ")
                for i, w in enumerate(words):
                    yield {"type": "chunk", "content": w + (" " if i < len(words)-1 else "")}
                    await asyncio.sleep(0.03)  # Diperlambat agar natural
                if cached.get("chartType"):
                    yield {"type": "chart_config", "chart": cached["chartType"], "data": cached.get("chartData")}
                yield {"type": "done",
                       "time_ms": int((time.time()-start_time)*1000),
                       "citation": "Semantic Cache (Hit)"}
                return
            pipeline = self.data_pipeline
        else:
            pipeline = self.greeting_pipeline

        # 3. Run ADK pipeline
        runner = Runner(
            agent=pipeline,
            session_service=self.persistence,
            app_name="rag_pro_nlq" 
        )
        content_msg = Content(role="user", parts=[Part.from_text(text=message)])

        final_response, sql_executed, chart_data, chart_type = "", None, None, None
        # MCP tools are named <domain>_query_data (finance_query_data, hr_query_data, ...)
        QUERY_TOOL_SUFFIX = "_query_data"

        events = iterate_with_deadline(
            runner.run_async(user_id=user_id, session_id=session_id, new_message=content_msg),
            NLQ_TIMEOUT_S,
        )
        try:
            async for event in events:
                # Emit SQL
                if hasattr(event, "content") and event.content and getattr(event.content, "parts", None):
                    for part in event.content.parts:
                        if (getattr(part, "function_call", None)
                                and part.function_call.name.endswith(QUERY_TOOL_SUFFIX)):
                            sql_executed = part.function_call.args.get("sql", "Unknown SQL")
                            yield {"type": "sql", "sql": sql_executed}

                # Stream text
                if (getattr(event, "author", None) == "GeneratorAgent"
                        and hasattr(event, "content") and event.content
                        and getattr(event.content, "parts", None)):
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            import asyncio
                            words = part.text.split(" ")
                            for i, w in enumerate(words):
                                yield {"type": "chunk", "content": w + (" " if i < len(words)-1 else "")}
                                await asyncio.sleep(0.03)  # Diperlambat agar natural
                            final_response += part.text

                # Chart state
                if (hasattr(event, "actions") and event.actions
                        and getattr(event.actions, "state_delta", None)):
                    if "chart_ready" in event.actions.state_delta:
                        chart_type = event.actions.state_delta.get("chart_type")
                        chart_data = event.actions.state_delta.get("chart_data")
                        yield {"type": "chart_config", "chart": chart_type, "data": chart_data}
        except Exception as e:
            timed_out = is_timeout_error(e)
            logging.exception("NLQ pipeline failed (timeout=%s)", timed_out)
            detail = (f"Data agent tidak merespons dalam {int(NLQ_TIMEOUT_S)} detik. Silakan coba lagi."
                      if timed_out else "Data agent gagal memproses pertanyaan. Silakan coba lagi.")
            yield {"type": "error", "detail": detail, "timeout": timed_out}
            return

        time_ms = int((time.time()-start_time)*1000)
        if intent == "Data Query" and final_response and sql_executed:
            set_semantic_cache(message, {
                "content": final_response, "chartType": chart_type, "chartData": chart_data
            }, encoder=get_gemini_encoder(), namespace="nlq")
        yield {"type": "done", "time_ms": time_ms,
               "citation": "BigQuery" if sql_executed else "Knowledge Base"}
