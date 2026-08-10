import json, time, logging
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
from semantic_router import Route, SemanticRouter
from langsmith import traceable


# ─── INTENT ROUTING ──────────────────────────────────────────────────────────
_DATA_KEYWORDS = {
    "berapa", "jumlah", "total", "rata-rata", "tampilkan", "tunjukkan",
    "daftar", "analisis", "bandingkan", "hitung", "cari",
    "tertinggi", "terendah", "terbesar", "terkecil", "top", "worst",
    "how many", "show me", "list", "count", "average", "compare",
    "distribution", "breakdown", "highest", "lowest", "what is",
    # Specific terms:
    "users", "events"
}

_router_layer = None

def get_semantic_router():
    global _router_layer
    if _router_layer is None:
        greeting_route = Route(
            name="Greeting",
            utterances=[
                "halo", "hai", "hello", "hi", "selamat pagi",
                "siapa kamu", "apa kabar", "terima kasih", "thanks",
                "help", "bantuan", "apa yang bisa kamu lakukan",
            ]
        )
        # Assuming you'd have a Data Query route here if using SemanticRouter purely,
        # but the logic below falls back to basic keyword/greeting match.
        _router_layer = SemanticRouter(
            encoder=get_encoder(), routes=[greeting_route], auto_sync="local"
        )
    return _router_layer

@traceable(name="intent_detection")
def _detect_intent(text: str) -> str:
    lower = text.lower()
    if any(kw in lower for kw in _DATA_KEYWORDS):
        return "Data Query"
    try:
        route = get_semantic_router()(text)
        if route and route.name == "Greeting":
            return "Greeting"
    except Exception as e:
        logging.warning(f"Semantic router failed: {e}")
    if any(w in lower for w in {"halo","hai","hello","hi","thanks","help","selamat","terima"}):
        return "Greeting"
    # For integration with RAG, we might return "Knowledge Base" for unknown stuff
    # But since we use intent routing to decide Data vs Knowledge in api.py,
    # let's only return Data Query if it explicitly matches data keywords, otherwise Knowledge Base.
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
        output_key="final_response"
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
                )
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
            # 2. Semantic cache
            cached = get_semantic_match(message)
            if cached:
                import asyncio
                words = cached.get("content", "").split(" ")
                for i, w in enumerate(words):
                    yield {"type": "chunk", "content": w + (" " if i < len(words)-1 else "")}
                    await asyncio.sleep(0.01)
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
        QUERY_TOOL_NAME = "query_data" 

        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content_msg
        ):
            # Emit SQL
            if hasattr(event, "content") and event.content and getattr(event.content, "parts", None):
                for part in event.content.parts:
                    if (getattr(part, "function_call", None)
                            and part.function_call.name == QUERY_TOOL_NAME):
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
                            await asyncio.sleep(0.015)
                        final_response += part.text

            # Chart state
            if (hasattr(event, "actions") and event.actions
                    and getattr(event.actions, "state_delta", None)):
                if "chart_ready" in event.actions.state_delta:
                    chart_type = event.actions.state_delta.get("chart_type")
                    chart_data = event.actions.state_delta.get("chart_data")
                    yield {"type": "chart_config", "chart": chart_type, "data": chart_data}

        time_ms = int((time.time()-start_time)*1000)
        if intent == "Data Query" and final_response and sql_executed:
            set_semantic_cache(message, {
                "content": final_response, "chartType": chart_type, "chartData": chart_data
            })
        yield {"type": "done", "time_ms": time_ms,
               "citation": "BigQuery" if sql_executed else "Knowledge Base"}
