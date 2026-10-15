<div align="center">

# 🧠 Knowlytics Intelligence

### Enterprise-Grade Multi-Agent RAG Platform

*A production-ready, AI-powered knowledge intelligence system that combines Retrieval-Augmented Generation, multi-agent orchestration, natural language querying, and automated report synthesis into a single unified platform.*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![GCP](https://img.shields.io/badge/Cloud_Run-GCP-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)](https://cloud.google.com/run)
[![Weaviate](https://img.shields.io/badge/Weaviate-Vector_DB-FA7535?style=for-the-badge)](https://weaviate.io)

</div>

---

## 📌 Overview

**Knowlytics Intelligence** is a full-stack, enterprise AI platform built to solve the critical challenge of *unlocking knowledge trapped in documents and databases*. It goes beyond a simple chatbot — it is an intelligent, multi-modal knowledge engine capable of:

- Answering questions grounded on private enterprise documents with cited sources
- Querying structured relational databases using plain natural language (NLQ)
- Performing deep data analysis on CSV/Excel files and BigQuery datasets
- Autonomously generating structured corporate reports by combining multiple data sources

The platform is designed with a **clean architecture** (Domain → Application → Infrastructure → Interface), is fully containerized, and is **ready for deployment on Google Cloud Run**.

---

## 🔴 The Problem

Modern enterprises face three compounding knowledge challenges:

1. **Information Silos**: Critical knowledge is fragmented across hundreds of PDF policies, Word documents, and spreadsheets — inaccessible and unsearchable.
2. **Data Accessibility Gap**: Non-technical stakeholders cannot query structured databases or analyze raw data without dedicated analyst support, creating bottlenecks.
3. **Reporting Overhead**: Synthesizing insights from both documents *and* databases into a cohesive report is manual, slow, and error-prone.

Generic LLM chatbots fail here because they hallucinate, have no access to private data, and cannot reason across structured and unstructured sources simultaneously.

---

## ✅ The Solution

Knowlytics Intelligence addresses all three problems with a unified, agentic approach:

| Problem | Solution |
|---|---|
| Document Silos | Semantic vector search via Weaviate + contextual citation in every response |
| Data Access Gap | Natural Language to SQL agent (NLQ) with Google BigQuery and MCP Toolbox |
| Report Overhead | 3-agent autonomous Report Builder (Plan → Extract → Write) |

Every response is grounded in real data, traceable via Arize Phoenix, and protected by LLM-based security guardrails.

---

## ✨ Core Features

### 🗣️ 5-Mode Intelligent Chat
An adaptive RAG chat engine with multiple reasoning modes selectable per query:

| Mode | Description | Best For |
|---|---|---|
| **Fast** | Standard RAG with immediate streaming response | Quick factual lookups |
| **Summarize** | Structured Markdown summary of retrieved context | Document overviews |
| **Thinking** | Deep, structured response with Qwen 27B model | Complex multi-part questions |
| **Reasoning** | 5-stage agentic pipeline (Plan → Search × N → Reflect → Generate) | Multi-hop research questions |
| **Deep Analytic** | Lightweight in-memory GraphRAG using NetworkX | Entity-relationship analysis |

### 💬 Natural Language Query (NLQ) to BigQuery
Converts plain-language questions directly into Google BigQuery SQL queries across 4 enterprise datasets: **Finance, HR, Legal, and Marketing**. The NLQ agent uses the Google ADK + MCP Toolbox for robust, tool-calling-based query execution, returning both narrative answers and interactive chart configurations.

### 📊 Data Analysis Engine
- **File Upload Analysis**: Drag-and-drop CSV/Excel files for instant AI-powered statistical analysis, generating 5 structured insights with interactive Recharts visualizations.
- **BigQuery Analysis**: Analyze live BigQuery tables directly from the UI with the same deep-insight pipeline.

### 📄 Multi-Agent Report Builder
An autonomous 3-agent pipeline orchestrated with **Google ADK** (Agent Development Kit):
1. **Planner Agent**: Decomposes the user's prompt into a structured JSON plan of SQL queries and RAG queries.
2. **Extraction Worker Agent**: Executes the plan in parallel — running SQL via MCP Toolbox and RAG via Weaviate.
3. **Writer Agent**: Synthesizes all extracted context into a professional, long-form Markdown report with Executive Summary, sections, tables, and data narratives.

All report progress is streamed live to the UI via Server-Sent Events (SSE).

### 🔒 LLM-Based Security Guardrails
Every user input is validated by an LLM-as-Judge security layer powered by **Guardrails-AI**:
- Toxicity & hate speech detection
- Prompt injection & jailbreak prevention
- PII (Personally Identifiable Information) filtering
- Off-topic request blocking
- Political content restriction

### 📈 LLM Observability & Evaluation
- **Arize Phoenix**: Real-time distributed tracing of every LLM call — latency, token usage, span-by-span breakdown (retrieval → rerank → generation).
- **RAGAS Evaluation**: Automated offline evaluation suite measuring Context Precision, Answer Relevancy, and Faithfulness against a golden test dataset.

---

## 🏗️ Architecture & Workflow

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                       │
│  ChatInterface │ DataAnalysis │ ReportBuilder │ KnowledgeBase    │
└─────────────────────────┬───────────────────────────────────────┘
                           │  REST + SSE (Server-Sent Events)
┌─────────────────────────▼───────────────────────────────────────┐
│                   INTERFACE LAYER (FastAPI)                       │
│   /chat  │  /data-analysis  │  /report  │  /documents  │  /auth  │
│                       Rate Limiter                                │
└─────┬──────────────┬───────────────────┬────────────────────────┘
      │              │                   │
┌─────▼──────┐ ┌─────▼──────┐   ┌───────▼────────┐
│ APPLICATION│ │ APPLICATION│   │  APPLICATION   │
│  RAG       │ │  NLQ       │   │  Report Builder│
│  Pipeline  │ │  Agent     │   │  (ADK Pipeline)│
│            │ │            │   │                │
│ ┌────────┐ │ │            │   │  ┌──Planner──┐ │
│ │Fast    │ │ │  BigQuery  │   │  │ ┌Extract┐ │ │
│ │Reason  │ │ │  MCP Tools │   │  │ │Writer │ │ │
│ │GraphRAG│ │ │            │   │  └──────────┘ │ │
│ └────────┘ │ └────────────┘   └───────────────┘
└─────┬──────┘
      │
┌─────▼─────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                         │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │   Weaviate  │  │  Groq / OR   │  │  Google Firestore      │ │
│  │ Vector Store│  │  LLM Router  │  │  (knowldege-mi DB)     │ │
│  └─────────────┘  └──────────────┘  └───────────────────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │Arize Phoenix│  │ Google       │  │  Guardrails-AI         │ │
│  │  Tracing    │  │ BigQuery     │  │  Safety Layer          │ │
│  └─────────────┘  └──────────────┘  └───────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### RAG Chat Workflow

```
User Query
    │
    ▼
[1. Guardrail Check] ─── UNSAFE ──► Blocked Response
    │
    │ SAFE
    ▼
[2. Intent Detection] ─── NLQ ──► BigQuery Agent Pipeline
    │
    │ RAG / Default
    ▼
[3. Mode Router]
    │
    ├─ fast / summarize / thinking ──► [Standard RAG]
    │                                        │
    │                                   Vectorstore → Retrieve
    │                                        │
    │                                   Rerank (Cross-encoder)
    │                                        │
    │                                   LLM Generation (Stream)
    │                                        │
    │                                   Citation Extraction
    │
    └─ reasoning / deep_analytic ──► [Async Agent Pipeline]
                                          │
                                     (reasoning) 5-Stage Agent:
                                     Plan → Sub-task Search × N
                                          → Reflect → Generate
                                          │
                                     (deep_analytic) GraphRAG:
                                     Retrieve → Entity Extract
                                          → NetworkX Graph Build
                                          → BFS Traversal → Generate
```

---

## 🛠️ Technology Stack

### Backend
| Category | Technology | Purpose |
|---|---|---|
| **Framework** | FastAPI | High-performance async API with SSE streaming |
| **LLM Providers** | Groq, OpenRouter, Google Gemini | Multi-provider LLM routing with fallback chains |
| **Vector Database** | Weaviate Cloud | Semantic document search & embedding storage |
| **Agent Framework** | Google ADK (Agent Development Kit) | Multi-agent orchestration (Report Builder, NLQ) |
| **Data Warehouse** | Google BigQuery | Structured enterprise data (Finance, HR, Legal, Marketing) |
| **Database** | Firestore (`knowldege-mi`) | User data, chat history, knowledge base metadata |
| **MCP Toolbox** | Google MCP Toolbox | Type-safe BigQuery tool-calling for agents |
| **Observability** | Arize Phoenix | Distributed LLM tracing & latency monitoring |
| **Evaluation** | RAGAS | RAG quality metrics (Precision, Relevancy, Faithfulness) |
| **Security** | Guardrails-AI | LLM-as-Judge safety validation layer |
| **Graph** | NetworkX | In-memory entity graph for Deep Analytic mode |
| **Tracing** | LangSmith | Chain-level tracing and debugging |
| **Auth** | JWT (python-jose) | Stateless token-based authentication |
| **Rate Limiting** | SlowAPI | Per-user request rate limiting |

### LLM Registry (Multi-Model)
| Model Key | Provider | Context Window | Best For |
|---|---|---|---|
| `gemma-4-31b-it` | OpenRouter | 131K | RAG & summarization |
| `qwen3.6-27b` | Groq | 131K | Deep reasoning (Thinking mode) |
| `gpt-oss-20b` | OpenRouter | 262K | Fast reliable conversation |
| `llama-3.3-70b-versatile` | Groq | 128K | Security guard, fast queries |
| `gemini-flash-lite` | Google | — | Report Builder agents |
| `llama-3.2-vision` | Groq | — | Vision/image document queries |

### Frontend
| Technology | Purpose |
|---|---|
| **Next.js 14** (App Router) | React framework with SSR/SSE support |
| **TypeScript** | Type-safe component development |
| **Tailwind CSS** | Utility-first styling system |
| **Framer Motion** | Smooth UI animations and transitions |
| **Recharts** | Interactive data visualization for analysis results |
| **Lucide React** | Icon library |

### Infrastructure & DevOps
| Technology | Purpose |
|---|---|
| **Google Cloud Run** | Serverless container deployment (primary) |
| **Google Firestore** | NoSQL document database (production persistence) |
| **Google BigQuery** | Managed data warehouse for enterprise datasets |
| **Docker / Docker Compose** | Containerization & local dev orchestration |
| **Weaviate Cloud** | Managed vector database |
| **Vercel** | Frontend deployment |

---

## ⚖️ Design Tradeoffs

### 1. Multi-LLM Routing vs. Single-Provider
**Decision**: Route across Groq, OpenRouter, and Google Gemini with provider-specific model keys and fallback chains.

**Tradeoff**: Added orchestration complexity and potential inconsistency across providers vs. cost optimization, higher availability, and the ability to use the *best* model for each specific task (fast guard → `llama-70b`; deep thinking → `qwen 27b`; agents → `gemini-flash`).

### 2. Lightweight GraphRAG (NetworkX) vs. Dedicated Graph DB (Neo4j)
**Decision**: Build a per-query in-memory entity graph using NetworkX instead of a persistent Neo4j instance.

**Tradeoff**: Less comprehensive graph topology vs. **zero infrastructure dependency**, instant cold starts on Cloud Run, and memory efficiency (graph is cleared after each response). For the scale of enterprise document queries, the regex-based entity extraction + in-memory BFS is sufficient.

### 3. Google ADK for Multi-Agent vs. LangGraph
**Decision**: Use Google ADK's `SequentialAgent` + `LlmAgent` + `BaseAgent` primitives for the Report Builder pipeline.

**Tradeoff**: ADK is newer and has less community tooling than LangGraph vs. native integration with Gemini models, the MCP Toolbox ecosystem, and first-class support for streaming events out of the box.

### 4. SSE (Server-Sent Events) vs. WebSockets
**Decision**: Use FastAPI `StreamingResponse` with SSE for all streaming chat, reasoning steps, and report progress.

**Tradeoff**: Unidirectional only vs. **simplicity, statelessness, HTTP/2 compatibility**, automatic reconnect, and zero additional infrastructure needed — perfectly suited for Cloud Run's request-response model.

### 5. PostgreSQL → Firestore Migration
**Decision**: Migrate from PostgreSQL (self-hosted) to Google Firestore for user/session data.

**Tradeoff**: Losing ACID transactions and relational query capabilities vs. **zero infrastructure management**, automatic scaling, seamless integration with the GCP ecosystem (Cloud Run + Firestore are first-class partners), and eliminating the need to maintain a Cloud SQL instance.

---

## ⚠️ Known Limitations

1. **Embedding Quality**: Weaviate uses pre-configured embeddings. Changing the embedding model requires a full re-indexing of the knowledge base.

2. **GraphRAG Entity Extraction**: The Deep Analytic mode uses regex-based entity extraction (no spaCy/NLP model) for memory efficiency. This may miss implicit relationships in complex documents.

3. **Report Builder SQL Agent**: The `ExtractionWorkerAgent` uses ephemeral `InMemorySessionService` for each SQL sub-task runner, which means SQL context is not shared between sub-queries within a single report run.

4. **Rate Limiting**: Current rate limits are configured globally (SlowAPI). Per-user, per-plan rate limits are not yet implemented.

5. **No Real-Time KB Sync**: Documents indexed into Weaviate and metadata stored in Firestore's `knowledge_base` collection are not automatically synchronized — manual re-sync is required after deletions or updates.

6. **Vision Mode**: Image-based document analysis (via `llama-3.2-vision`) is functional but limited to images directly provided in the chat context, not images embedded inside indexed documents.

---

## 🚀 Deployment — Google Cloud Run

### Prerequisites
- Docker installed
- Google Cloud CLI (`gcloud`) authenticated
- A GCP Project with Cloud Run, Cloud Build, and Artifact Registry enabled

### Build & Push to Artifact Registry
```bash
# Set your project and region
export PROJECT_ID=""
export REGION=asia-southeast1
export IMAGE=asia-southeast1-docker.pkg.dev/$PROJECT_ID/knowlytics/backend:latest

# Build and push
docker build -f deployments/Dockerfile -t $IMAGE ./backend
docker push $IMAGE
```

### Deploy Backend to Cloud Run
```bash
gcloud run deploy knowlytics-backend \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GROQ_API_KEY=your_key,OPENROUTER_API_KEY=your_key,WEAVIATE_URL=your_url,WEAVIATE_API_KEY=your_key,GEMINI_API_KEY=your_key \
  --set-secrets GOOGLE_APPLICATION_CREDENTIALS=firestore-key:latest \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 3600
```

### Deploy Frontend to Vercel
```bash
cd frontend
vercel deploy --prod
```

### Local Development
```bash
# 1. Start infrastructure services
docker-compose -f deployments/docker-compose.yml up -d db weaviate

# 2. Start backend
cd backend
python -m venv venv && source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.local .env
uvicorn src.interface.api:app --reload --host 0.0.0.0 --port 8000

# 3. Start frontend
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Environment Variables
```env
# LLM Providers
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key

# Vector Database
WEAVIATE_URL=your_weaviate_cloud_url
WEAVIATE_API_KEY=your_weaviate_key

# Observability
PHOENIX_API_KEY=your_arize_phoenix_key
PHOENIX_COLLECTOR_ENDPOINT=your_phoenix_endpoint

# Database (Firestore via Service Account)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firestore-key.json

# HuggingFace (for reranker model)
HUGGINGFACE_TOKEN=your_hf_token
```

---


## 📂 Project Structure

```
knowlytics-intelligence/
├── backend/
│   ├── src/
│   │   ├── domain/               # Business logic, entities, security guardrails
│   │   │   ├── agents/           # Agent prompt definitions
│   │   │   ├── prompt/           # Prompt builders
│   │   │   └── security/         # Guardrails-AI safety layer
│   │   ├── application/          # Use cases & pipeline orchestration
│   │   │   ├── rag/              # RAG pipeline, GraphRAG, Reasoning Agent, RAGAS Evaluator
│   │   │   ├── nlq/              # NLQ agent (Natural Language to BigQuery)
│   │   │   ├── report/           # Multi-agent Report Builder pipeline
│   │   │   └── evaluation/       # Batch RAGAS evaluation harness
│   │   ├── infrastructure/       # External services & adapters
│   │   │   ├── llm/              # LLM model registry, routing & fallback chains
│   │   │   ├── tools/            # MCP Toolbox config (BigQuery tools)
│   │   │   ├── monitoring/       # Arize Phoenix OTel setup
│   │   │   └── config/           # Environment & configuration management
│   │   └── interface/            # FastAPI routes & API layer
│   │       ├── routes/           # chat, documents, data_analysis, report, auth, history
│   │       └── rate_limiter.py   # SlowAPI rate limiting middleware
│   ├── script/
│   │   └── migrate_to_firestore.py   # One-time PostgreSQL → Firestore migration
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages
│   │   └── components/           # React components (ChatInterface, DataAnalysis, etc.)
│   └── package.json
├── deployments/
│   ├── Dockerfile                # Production container image
│   ├── docker-compose.yml        # Local dev stack (Postgres, Weaviate, MLflow)
│   └── k8s/                      # Kubernetes manifests (optional)
└── README.md
```

---

## 📜 License

This project is built as a portfolio showcase. All rights reserved © 2026 Simon SK.

---

<div align="center">
<i>Built with ❤️ as part of a AI Engineering designed to reflect production-grade engineering practices.</i>
</div>
