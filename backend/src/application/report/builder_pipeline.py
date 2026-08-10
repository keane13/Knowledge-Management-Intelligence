import json
import logging
import asyncio
from typing import AsyncGenerator, Any, Dict

from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.adk.agents import LlmAgent, SequentialAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.genai.types import GenerateContentConfig, ToolConfig, FunctionCallingConfig, Content, Part

from src.infrastructure.tools.mcp_toolbox import toolset
from src.domain.agents.nlq_agent.prompts import SEARCH_AGENT_PROMPT
from src.application.rag.pipeline import run_rag
from langsmith import traceable

logger = logging.getLogger(__name__)

# --- AGENT 1: PLANNER ---
PLANNER_PROMPT = """
You are the Report Planner Agent. Your job is to decompose the user's complex report request into specific sub-queries.
You must return a valid JSON object with EXACTLY this structure:
{
    "sql_queries": ["query 1 for the database", "query 2 for the database"],
    "rag_queries": ["query 1 for the knowledge base documents", "query 2 for the knowledge base documents"]
}
If a source is not needed, leave the array empty.
Focus on extracting quantitative data from SQL and qualitative data/SOPs from RAG.
DO NOT return any markdown formatting around the JSON. Only return the raw JSON object.
"""

def get_planner_agent() -> LlmAgent:
    return LlmAgent(
        name="PlannerAgent",
        model="gemini-flash-lite-latest", # Fast routing model
        instruction=PLANNER_PROMPT,
        description="Decomposes a request into SQL and RAG queries.",
        output_key="planner_plan"
    )

# --- AGENT 2: EXTRACTION WORKER ---
class ExtractionWorkerAgent(BaseAgent):
    name: str = "ExtractionWorkerAgent"
    description: str = "Executes the plan by running RAG and SQL queries, combining results."
    sql_agent: LlmAgent = None

    def __init__(self, model_name: str = "gemini-3-flash-preview", **kwargs):
        super().__init__(**kwargs)
        self.sql_agent = LlmAgent(
            name="SearchDataWorker",
            model=model_name,
            instruction=SEARCH_AGENT_PROMPT,
            tools=[toolset],
            output_key="worker_sql_result",
            generate_content_config=GenerateContentConfig(
                tool_config=ToolConfig(
                    function_calling_config=FunctionCallingConfig(mode="AUTO")
                )
            )
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        plan_str = ctx.session.state.get("planner_plan", "{}")
        
        # Clean JSON string just in case
        plan_str = plan_str.strip()
        if plan_str.startswith("```json"):
            plan_str = plan_str[7:]
        if plan_str.startswith("```"):
            plan_str = plan_str[3:]
        if plan_str.endswith("```"):
            plan_str = plan_str[:-3]

        try:
            plan = json.loads(plan_str)
        except json.JSONDecodeError:
            plan = {"sql_queries": [], "rag_queries": []}

        sql_queries = plan.get("sql_queries", [])
        rag_queries = plan.get("rag_queries", [])

        yield Event(actions=EventActions(state_delta={"extraction_status": "started", "plan": plan}))

        extracted_context = "### EXTRACTED DATA CONTEXT ###\n\n"

        # 1. Execute SQL Queries
        for query in sql_queries:
            yield Event(actions=EventActions(state_delta={"current_extraction": f"SQL: {query}"}))
            # Run the SQL agent manually for this sub-query
            try:
                # Mocking a direct call to the underlying LlmAgent logic for simplicity,
                # In a real ADK flow we could use sub-runners, but for now we'll just format the prompt.
                runner_msg = Content(role="user", parts=[Part.from_text(text=query)])
                
                # We can use the agent's execute directly or we can just emit an event indicating SQL data.
                # To keep it robust without reinventing runner state, we'll invoke the tool directly or use the agent.
                # Actually, the simplest way is to yield a sub-agent execution, but BaseAgent doesn't natively do that in this loop easily.
                # Let's run it via a temporary runner or just call the LLM directly.
                from google.adk.runners import Runner
                from google.adk.sessions import InMemorySessionService
                
                temp_runner = Runner(agent=self.sql_agent, session_service=InMemorySessionService())
                sql_result_str = ""
                async for evt in temp_runner.run_async(user_id="sys", session_id="temp", new_message=runner_msg):
                     if hasattr(evt, "content") and evt.content and getattr(evt.content, "parts", None):
                        for p in evt.content.parts:
                            if getattr(p, "text", None):
                                sql_result_str += p.text
                
                extracted_context += f"#### Data Warehouse Result for '{query}':\n{sql_result_str}\n\n"
            except Exception as e:
                logger.error(f"SQL extraction failed: {e}")

        # 2. Execute RAG Queries
        for query in rag_queries:
            yield Event(actions=EventActions(state_delta={"current_extraction": f"Docs: {query}"}))
            try:
                # We use the existing run_rag function
                # For worker extraction, we don't need a stream, just the context
                rag_res = run_rag(query, mode="fast", stream=False)
                context_texts = rag_res.get("contexts", [])
                
                if context_texts:
                    combined_ctx = "\\n...\\n".join(context_texts)
                    extracted_context += f"#### Document Knowledge for '{query}':\n{combined_ctx}\n\n"
                else:
                    extracted_context += f"#### Document Knowledge for '{query}':\n(No relevant documents found)\n\n"
            except Exception as e:
                logger.error(f"RAG extraction failed: {e}")

        # Store combined context
        yield Event(actions=EventActions(state_delta={"extracted_context": extracted_context, "extraction_status": "done"}))
        yield Event()

# --- AGENT 3: WRITER ---
WRITER_PROMPT = """
You are an expert Corporate Report Writer.
You will be provided with heterogeneous context extracted from databases and documents.
Your task is to synthesize this data into a professional, cohesive, long-form Markdown report.

Guidelines:
- Include a clear title and an Executive Summary.
- Organize the report into logical sections with ## Headers.
- Use bullet points, bold text, and tables where appropriate to present data clearly.
- Maintain a professional, objective corporate tone.
- Integrate the quantitative data (from SQL) and qualitative data (from documents) seamlessly.

Extracted Context:
{{extracted_context}}
"""

def get_writer_agent(model_name: str = "gemini-flash-lite-latest") -> LlmAgent:
    return LlmAgent(
        name="WriterAgent",
        model=model_name,
        instruction=WRITER_PROMPT,
        description="Synthesizes extracted context into a draft report.",
        output_key="draft_report"
    )

# --- AGENT 4: REFLECTION ---
REFLECTION_PROMPT = """
You are an expert Editor and Quality Assurance Agent.
You will receive a draft corporate report. Your job is to deeply reflect on it and produce a polished, final version.

Guidelines:
- Fix any grammatical errors or awkward phrasing.
- Ensure the tone is strictly professional, objective, and corporate.
- Improve the structure and formatting (use Markdown effectively, e.g., clean tables, bolding key metrics).
- DO NOT hallucinate new data; strictly rely on the data presented in the draft.
- Return ONLY the final polished markdown text without any conversational filler.

Draft Report:
{{draft_report}}
"""

def get_reflection_agent(model_name: str = "gemini-flash-lite-latest") -> LlmAgent:
    return LlmAgent(
        name="ReflectionAgent",
        model=model_name,
        instruction=REFLECTION_PROMPT,
        description="Reflects on the draft report and polishes it.",
        output_key="final_report"
    )

# --- PIPELINE BUILDER ---
class ReportBuilderUseCase:
    def __init__(self, persistence_service, text_model: str = "gemini-flash-lite-latest"):
        self.persistence = persistence_service
        self.text_model = text_model

        self.pipeline = SequentialAgent(
            name="ReportBuilderPipeline",
            sub_agents=[
                get_planner_agent(),
                ExtractionWorkerAgent(model_name=self.text_model),
                get_writer_agent(model_name=self.text_model),
                get_reflection_agent(model_name=self.text_model)
            ],
            description="End-to-end report building pipeline."
        )

    @traceable(name="execute_report_builder")
    async def execute(self, session_id: str, user_id: str, prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        from google.adk.runners import Runner
        
        runner = Runner(
            agent=self.pipeline,
            session_service=self.persistence,
            app_name="rag_pro_report_builder",
            auto_create_session=True
        )
        
        msg = Content(role="user", parts=[Part.from_text(text=prompt)])
        
        yield {"type": "status", "status": "PLANNING", "message": "Decomposing request..."}

        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
            # Intercept Planner output
            if getattr(event, "author", None) == "PlannerAgent":
                pass # We can optionally emit tokens here if we want to show the JSON

            # Intercept Extraction Status
            if hasattr(event, "actions") and event.actions and getattr(event.actions, "state_delta", None):
                delta = event.actions.state_delta
                if "extraction_status" in delta and delta["extraction_status"] == "started":
                    yield {"type": "status", "status": "EXTRACTING", "message": "Extracting data from sources...", "plan": delta.get("plan")}
                if "current_extraction" in delta:
                    yield {"type": "extraction_update", "detail": delta["current_extraction"]}
                if "extraction_status" in delta and delta["extraction_status"] == "done":
                    yield {"type": "status", "status": "WRITING", "message": "Synthesizing final report..."}

            # We will not stream WriterAgent to avoid double-printing in UI.
            # Instead, we wait for ReflectionAgent to start and stream that.
            if getattr(event, "author", None) == "ReflectionAgent":
                # Check if it's the first reflection chunk to update status
                if not getattr(self, "_reflection_started", False):
                    yield {"type": "status", "status": "REFLECTING", "message": "Memoles laporan akhir (Reflection)..."}
                    self._reflection_started = True

                if hasattr(event, "content") and event.content and getattr(event.content, "parts", None):
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            yield {"type": "chunk", "content": part.text}

        yield {"type": "done"}
