import sys
import os
sys.path.append(os.getcwd())

import json
import random
from src.application.rag.loader import load_documents
from src.infrastructure.config.configs import DOCS_PATH
from src.infrastructure.llm.llm import client

def generate_qa_pair(context):
    prompt = f"""
    Context:
    {context}
    
    Task:
    Generate a single question and its corresponding answer based ONLY on the context above.
    The question should be specific and answerable from the context.
    The answer should be concise but complete.
    
    Output format (JSON):
    {{
        "question": "The question here",
        "ground_truth": "The answer here"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error generating QA: {e}")
        return None

def main():
    print("Loading documents...")
    docs = load_documents(DOCS_PATH)
    print(f"Loaded {len(docs)} document chunks.")
    
    # Simple chunking if docs are pages, or just use page_content directly
    # Assuming docs are pages from PyPDFLoader
    
    dataset = []
    
    # Sample 5 random pages/docs to generate questions from
    selected_docs = random.sample(docs, min(len(docs), 20))
    
    print("Generating QA pairs...")
    for i, doc in enumerate(selected_docs):
        print(f"Processing doc {i+1}/{len(selected_docs)}")
        qa = generate_qa_pair(doc.page_content)
        if qa:
            dataset.append({
                "question": qa["question"],
                "ground_truth": qa["ground_truth"]
            })
            
    output_path = "data/ragas_eval.json"
    print(f"Saving {len(dataset)} pairs to {output_path}")
    
    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=2)

if __name__ == "__main__":
    main()
