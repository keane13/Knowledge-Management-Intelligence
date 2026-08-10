import sys
import os
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.application.rag.pipeline import run_rag
from unittest.mock import MagicMock, patch

def test_pipeline():
    print("Testing RAG Pipeline...")
    
    # Mocking external dependencies to avoid needing real API keys/connections during verify
    with patch("rag.pipeline.get_vectorstore") as mock_get_vs, \
         patch("rag.pipeline.retrieve") as mock_retrieve, \
         patch("rag.pipeline.build_prompt") as mock_build_prompt, \
         patch("rag.pipeline.generate_answer") as mock_generate_answer, \
         patch("rag.pipeline.log_metrics") as mock_log_metrics:
        
        mock_vs = MagicMock()
        mock_get_vs.return_value = mock_vs
        
        mock_doc = MagicMock()
        mock_doc.page_content = "This is a test context."
        mock_retrieve.return_value = [mock_doc]
        
        mock_build_prompt.return_value = [{"role": "user", "content": "test"}]
        mock_generate_answer.return_value = "This is a test answer."
        
        # Test non-streaming
        print("Running non-streaming test...")
        answer, metrics, context = run_rag("What is this?", mode="fast", stream=False)
        
        assert answer == "This is a test answer."
        assert context == "This is a test context."
        assert "retrieval" in metrics
        assert "llm" in metrics
        print("Non-streaming test passed!")
        
        # Test streaming
        print("Running streaming test...")
        mock_generate_answer.return_value = iter(["chunk1", "chunk2"])
        answer_stream, context = run_rag("What is this?", mode="fast", stream=True)
        
        assert list(answer_stream) == ["chunk1", "chunk2"]
        assert context == "This is a test context."
        print("Streaming test passed!")

if __name__ == "__main__":
    try:
        test_pipeline()
        print("Verification completed successfully!")
    except Exception as e:
        print(f"Verification failed: {e}")
        sys.exit(1)
