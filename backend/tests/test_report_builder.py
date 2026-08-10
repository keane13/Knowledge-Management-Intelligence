import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.application.report.builder_pipeline import ReportBuilderUseCase
from google.adk.sessions import InMemorySessionService
from src.infrastructure.database import init_db

async def main():
    print("Initializing Database...")
    init_db()

    persistence = InMemorySessionService()
    try:
        await persistence.create_session("test_session_1")
    except Exception:
        pass
        
    use_case = ReportBuilderUseCase(persistence_service=persistence, text_model="gemini-2.0-flash-lite")

    prompt = "Buatkan laporan singkat tentang Q3 revenue dan gabungkan dengan strategi marketing dari dokumen SOP."
    print(f"Prompt: {prompt}")

    print("Executing Pipeline...")
    try:
        async for event in use_case.execute(session_id="test_session_1", user_id="test_user", prompt=prompt):
            if event["type"] == "status":
                print(f"[{event['status']}] {event.get('message', '')}")
                if "plan" in event:
                    print(f"Plan: {event['plan']}")
            elif event["type"] == "extraction_update":
                print(f"   -> Extracting: {event['detail']}")
            elif event["type"] == "chunk":
                print(event["content"], end="", flush=True)
            elif event["type"] == "done":
                print("\n\n[DONE] Pipeline completed.")
            elif event["type"] == "error":
                print(f"\n[ERROR] {event['message']}")
    except Exception as e:
        print(f"\n[EXCEPTION] {e}")

if __name__ == "__main__":
    asyncio.run(main())
