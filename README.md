# RAG Document Q&A System

A full-stack **Retrieval-Augmented Generation (RAG)** application that enables users to upload documents (PDF, DOCX, TXT), process them into searchable chunks, and ask natural language questions to get AI-generated answers grounded in the document content.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)               │
│  ┌─────────┐ ┌──────┐ ┌───────────┐ ┌───────────────┐  │
│  │ Sidebar │ │ Chat │ │ FileUpload│ │ ModelSelector │  │
│  └─────────┘ └──────┘ └───────────┘ └───────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP REST API (JSON)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 Backend (Django REST Framework)           │
│  ┌──────────────────────────────────────────────────┐   │
│  │              RAG Pipeline Engine                   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │   │
│  │  │ Chunking │ │ Hybrid   │ │ LLM Inference    │  │   │
│  │  │ (800ch)  │ │ Search   │ │ (Ollama / Groq)  │  │   │
│  │  └──────────┘ │ Vector   │ └──────────────────┘  │   │
│  │               │ + BM25   │                        │   │
│  │               └──────────┘                        │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌─────────────────┐          │
│  │ChromaDB  │ │ SQLite   │ │ Ollama Server   │          │
│  │(Vectors) │ │ (Django) │ │ (phi4-mini)     │          │
│  └──────────┘ └──────────┘ └─────────────────┘          │
└─────────────────────────────────────────────────────────┘
```

## ⚙️ Tech Stack

### Backend

| Technology | Purpose |
|-----------|---------|
| **Python 3.12** | Core programming language |
| **Django 5.1** | Web framework for API & ORM |
| **Django REST Framework** | REST API endpoints |
| **SQLite** | Database for documents, sessions, messages |
| **ChromaDB 0.5.18** | Vector database for embedding storage & similarity search |
| **sentence-transformers** | Embedding model (BAAI/bge-large-en-v1.5) |
| **rank-bm25** | BM25 Okapi keyword search for hybrid retrieval |
| **PyPDF2** | PDF text extraction |
| **python-docx** | DOCX text extraction |
| **Ollama** | Local LLM inference server (phi4-mini) |
| **Groq API** | Cloud LLM alternative (optional) |
| **python-decouple** | Environment configuration (.env) |

### Frontend

| Technology | Purpose |
|-----------|---------|
| **React 18** | UI component library |
| **Vite 6** | Build tool & dev server |
| **Axios** | HTTP client for API calls |
| **react-markdown** | Render AI responses with Markdown |
| **react-dropzone** | Drag-and-drop file upload |
| **react-icons** | UI icons |
| **react-hot-toast** | Toast notifications |
| **CSS Variables** | Theming (dark/light mode support) |

### DevOps

| Technology | Purpose |
|-----------|---------|
| **Docker** | Containerization |
| **docker-compose** | Multi-container orchestration |
| **Nginx** | Production reverse proxy |
| **GitHub Actions** | CI/CD pipelines |

## 🧠 Core RAG Pipeline

### 1. Document Processing

When a document is uploaded, it goes through 5 stages:

```
Upload → Extract Text → Chunk (800ch) → Embed (bge-large) → Store (ChromaDB + BM25)
```

**Text Extraction**: Supports PDF (with page tracking), DOCX, and TXT files.

**Chunking Strategy**: Recursive character text splitting with semantic boundary awareness:
- **Chunk Size**: 800 characters (optimized for LLM context windows)
- **Chunk Overlap**: 100 characters (preserves context between chunks)
- **Split Priority**: Paragraphs → Lines → Sentences → Character-level

### 2. Hybrid Search (Vector + BM25)

Uses **Reciprocal Rank Fusion (RRF)** to combine two retrieval methods:

```python
# RRF Formula
score = 1 / (k + rank)   # k = 60 (constant)

# Final Score
final_score = (vector_rrf × 0.6) + (keyword_rrf × 0.4)
```

| Method | Weight | Strengths |
|--------|--------|-----------|
| **Vector Search (ChromaDB)** | 60% | Semantic similarity, understands meaning |
| **BM25 Keyword Search** | 40% | Exact term matching, high precision |

**Why Hybrid?**
- Vector search alone misses exact keyword matches
- BM25 alone misses semantically similar terms
- Combined, they provide robust retrieval for all query types

### 3. LLM Inference

The retrieved context is fed to an LLM with a strict instruction prompt:

```
You are a document Q&A system. Answer using ONLY the context below.
If the answer is not present, say "I don't know based on the provided context."
Cite sources with [Source X] when using specific information.
```

| Provider | Model | Use Case |
|----------|-------|----------|
| **Ollama** (default) | phi4-mini:latest | Local, offline, private |
| **Groq** (optional) | llama-3.1-8b-instant | Cloud, faster inference |

### 4. Embedding Model

Using **BAAI/bge-large-en-v1.5** (1024 dimensions):
- State-of-the-art semantic embeddings
- Normalized embeddings for cosine similarity
- ~1.5GB model size (loaded lazily when first needed)

## 📁 Project Structure

```
rag-django-react/
├── backend/                          # Django Backend
│   ├── rag_api/                      # Django project settings
│   │   ├── settings.py               # Configuration (DB, Chroma, Models)
│   │   ├── urls.py                   # Root URL routing
│   │   ├── wsgi.py / asgi.py         # Server interfaces
│   │   └── ...
│   ├── documents/                    # Main app
│   │   ├── models.py                 # Document, ChatSession, ChatMessage
│   │   ├── views.py                  # All API endpoints
│   │   ├── serializers.py            # DRF serializers
│   │   ├── rag_pipeline.py           # Core RAG logic (1046 lines)
│   │   ├── ollama_manager.py         # Ollama server management
│   │   ├── utils.py                  # Helper functions
│   │   ├── admin.py                  # Django admin config
│   │   ├── apps.py                   # App config
│   │   ├── urls.py                   # App URL routing
│   │   └── migrations/               # DB migrations
│   ├── media/documents/              # Uploaded files
│   ├── chroma_db_v2/                 # Vector database
│   ├── db.sqlite3                    # Relational database
│   ├── manage.py                     # Django management
│   ├── requirements.txt              # Python dependencies
│   ├── Dockerfile                    # Backend Docker image
│   ├── .env                          # Environment variables
│   └── .env.example                  # Environment template
│
├── frontend/                         # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.jsx              # Chat interface + message display
│   │   │   ├── Chat.css              # Chat styling
│   │   │   ├── Sidebar.jsx           # Navigation + document list
│   │   │   ├── Sidebar.css           # Sidebar styling
│   │   │   ├── FileUpload.jsx        # Drag-and-drop upload
│   │   │   ├── FileUpload.css        # Upload styling
│   │   │   ├── ModelSelector.jsx     # Model/provider selection
│   │   │   ├── ModelSelector.css     # Model selector styling
│   │   │   └── Citation.jsx          # Source citation display
│   │   ├── App.jsx                   # Main app component
│   │   ├── App.css                   # App layout styling
│   │   ├── api.js                    # API client (axios)
│   │   ├── index.css                 # Global CSS + variables
│   │   └── main.jsx                  # Entry point
│   ├── index.html                    # HTML template
│   ├── package.json                  # Node dependencies
│   ├── vite.config.js                # Vite configuration
│   ├── Dockerfile                    # Frontend Docker image
│   └── nginx.conf                    # Nginx config (production)
│
├── docker-compose.yml                # Multi-container setup
├── .github/workflows/                # CI/CD pipelines
│   ├── backend-ci.yml
│   └── frontend-ci.yml
└── README.md                         # This file
```

## 🚀 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| **GET** | `/api/health/` | Health check + system status |
| **GET** | `/api/documents/` | List all documents |
| **POST** | `/api/documents/` | Upload a new document |
| **GET** | `/api/documents/:id/` | Get document details |
| **DELETE** | `/api/documents/:id/` | Delete a document |
| **POST** | `/api/documents/:id/process/` | Process document (chunk + embed) |
| **GET** | `/api/sessions/` | List all chat sessions |
| **POST** | `/api/sessions/` | Create a new chat session |
| **GET** | `/api/sessions/:id/` | Get session details |
| **DELETE** | `/api/sessions/:id/` | Delete a session |
| **GET** | `/api/sessions/:id/messages/` | Get session messages |
| **POST** | `/api/ask/` | Ask a question (RAG pipeline) |
| **GET** | `/api/models/ollama/` | List available Ollama models |
| **GET** | `/api/models/groq/` | List Groq models (if configured) |
| **GET** | `/api/status/ollama/` | Check Ollama server status |
| **GET** | `/api/status/vector/` | Vector database statistics |
| **POST** | `/api/ollama/manage/` | Manage Ollama (pull/remove models) |
| **GET** | `/api/logs/` | Query history logs |

### Key Endpoint: `/api/ask/`

Request:
```json
{
  "question": "What is the main topic?",
  "session_id": "uuid-here",
  "document_id": "uuid-here",
  "llm_provider": "ollama",
  "llm_model": "phi4-mini:latest"
}
```

Response:
```json
{
  "answer": "The main topic is energy consumption prediction... [Source 2]",
  "sources": [
    {
      "index": 1,
      "text": "This study focuses on...",
      "page": 3,
      "score": 0.59
    }
  ],
  "metadata": {
    "chunks_retrieved": 3,
    "llm_provider": "ollama",
    "llm_model": "phi4-mini:latest",
    "retrieval_method": "hybrid (vector + keyword)",
    "latency_ms": 39266,
    "embedding_model": "BAAI/bge-large-en-v1.5"
  }
}
```

## 📦 Data Models

### Document
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `title` | CharField(255) | Document title |
| `file` | FileField | Uploaded file |
| `file_type` | CharField(10) | pdf, docx, or txt |
| `file_size` | BigIntegerField | Size in bytes |
| `page_count` | IntegerField | Estimated pages |
| `uploaded_at` | DateTimeField | Upload timestamp |
| `processed` | BooleanField | Processing status |
| `chunk_count` | IntegerField | Number of chunks created |

### ChatSession
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `title` | CharField(255) | Session title |
| `document` | ForeignKey (Document) | Associated document |
| `created_at` | DateTimeField | Creation time |
| `updated_at` | DateTimeField | Last activity |

### ChatMessage
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `session` | ForeignKey (ChatSession) | Parent session |
| `role` | CharField(10) | user / assistant / system |
| `content` | TextField | Message text (Markdown) |
| `sources` | JSONField | Retrieved source chunks |
| `created_at` | DateTimeField | Message timestamp |

### QueryLog
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `question` | TextField | User's question |
| `answer` | TextField | AI's answer |
| `sources` | JSONField | Retrieved chunks |
| `llm_provider` | CharField(50) | ollama / groq |
| `llm_model` | CharField(100) | Model name used |
| `latency_ms` | IntegerField | Response time |

## 🎨 Frontend Components

### App.jsx (Root)
Central state management for:
- Sessions, messages, documents
- Model/provider selection
- Upload & processing triggers
- API coordination

### Sidebar
- **Sessions Panel**: List/create/delete chat sessions
- **Documents Panel**: List uploaded docs with process status
- **Status Panel**: Ollama server status + vector DB stats
- **Model Controls**: Open model selector

### Chat
- Message display with Markdown rendering
- Source citation with clickable `[Source X]` links
- Loading indicator during inference
- Document context indicator

### FileUpload
- Drag-and-drop file upload (PDF, DOCX, TXT)
- Progress feedback via toast notifications
- Auto-process after upload

### ModelSelector
- Provider selection (Ollama/Groq)
- Model dropdown populated from API
- Pull new models from Ollama library
- Server health monitoring

### Citation
- Source number, page reference
- Score display (vector + keyword hybrid scores)
- Expandable text preview

## 🛠️ Setup & Installation

### Prerequisites
- **Python 3.10+** (3.12 recommended)
- **Node.js 18+**
- **Ollama** (for local inference) — [Download](https://ollama.ai/download)

### 1. Clone & Setup Backend

```bash
# Clone the repository
git clone <repo-url>
cd rag-django-react

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate    # Mac/Linux

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env if needed (defaults work for local development)

# Run migrations
python manage.py migrate

# Start Django server
python manage.py runserver 8000
```

### 2. Setup Frontend

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

### 3. Setup Ollama (Required for LLM inference)

```bash
# Download and install Ollama from https://ollama.ai/download
# Then pull a model:
ollama pull phi4-mini:latest
# Or any other model:
ollama pull llama3.2:3b
ollama pull mistral:7b
```

### 4. Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000/api/
- **Django Admin**: http://localhost:8000/admin/

### Quick Setup Script
```bash
cd backend
run_setup.bat    # Windows
python verify_install.py   # Verify installation
```

## 🐳 Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Access at http://localhost:80
# Frontend at http://localhost:3000
# Backend at http://localhost:8000
```

## 🖥️ Usage

### 1. Upload a Document
- Click "Upload" in the sidebar
- Drag & drop or select a PDF, DOCX, or TXT file
- Processing starts automatically after upload

### 2. Process Documents
- Documents appear in the sidebar with "Processed" or "Pending" status
- Click the refresh button on a document to re-process it
- Each document gets chunked, embedded, and indexed

### 3. Ask Questions
- Select a document from the sidebar
- Type your question in the chat input
- The system retrieves relevant chunks and generates an answer
- Answers include citations from the source document

### 4. Model Management
- Open Model Selector from the sidebar
- Switch between Ollama (local) and Groq (cloud)
- Pull new models directly from the UI
- Monitor server status

## 🔬 Key Technical Details

### Chunking Algorithm
```
Input: Text with page markers
  → Split by double newlines (paragraphs)
  → Track page numbers via [Page N] markers
  → If paragraph > 800 chars, split by sentences
  → Maintain 100-char overlap at boundaries
  → Find semantic break points (., !, ?, \n) for clean overlaps
  → Output: List of {"text": str, "page": int, "chunk_index": int}
```

### Hybrid Search Fusion
```
query → Vector Search (ChromaDB) → Top-20 candidates with scores
query → BM25 Search (rank-bm25)  → Top-20 candidates with scores

For each candidate:
  fused_score = (vector_rrf × 0.6) + (keyword_rrf × 0.4)
  where rrf_score = 1 / (60 + rank)

Sort by fused_score, return Top-3 → LLM Context
```

### Embedding Normalization
```python
# bge-large-en-v1.5 normalizes embeddings by default
embeddings = model.encode(texts, normalize_embeddings=True)
# Cosine similarity = dot product (when normalized)
similarity = np.dot(query_embedding, chunk_embedding)
```

## 🏆 Advantages Over Normal LLMs

### 1. Grounded Answers (No Hallucinations)
| Aspect | Normal LLM | RAG System |
|--------|-----------|------------|
| **Knowledge Source** | Training data (stale) | Your documents (fresh) |
| **Hallucinations** | Common (makes up facts) | Minimized (uses only provided context) |
| **Citations** | None | `[Source 2] [Page 5]` |
| **"I don't know"** | Rare (will guess) | Built-in (when context is missing) |

### 2. Data Privacy
- **Normal LLM**: Sends your data to external servers (OpenAI, Google, etc.)
- **RAG System**: Runs locally with Ollama — **Your data never leaves your machine**
- **Optional Cloud**: Can use Groq API if configured, but defaults to local

### 3. Domain-Specific Expertise
- **Normal LLM**: General knowledge cutoff at training date
- **RAG System**: Can answer about your specific documents
  - Academic papers
  - Legal contracts
  - Technical manuals
  - Internal company docs
  - Research papers (any language)

### 4. Hybrid Search vs. Pure Vector
| Technique | Example Query | Vector | BM25 | Hybrid |
|-----------|--------------|--------|------|--------|
| Synonym matching | "automobile" → finds "car" | ✅ | ❌ | ✅ |
| Exact phrase | "Section 4.2.1" | ❌ | ✅ | ✅ |
| Semantic meaning | "How to fix error X" → finds troubleshooting steps | ✅ | ❌ | ✅ |
| Acronym search | "CNN" → finds "Convolutional Neural Network" | ❌ | ✅ | ✅ |

### 5. Cost Efficiency
- **Normal LLM API**: Pay per token (gets expensive with large documents)
- **RAG System**: One-time embedding cost, then free inference
  - No per-query API costs
  - No data transfer fees
  - Unlimited questions once indexed

### 6. Transparency
- **Normal LLM**: Black box — no idea why it gave that answer
- **RAG System**: Full traceability
  - See exactly which chunks were retrieved
  - View source pages and scores
  - Inspect both vector and keyword contributions

### 7. Continuous Learning
- Upload new documents anytime
- Re-process existing documents
- Switch between different LLM models
- Compare performance across providers

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| **Embedding Model** | BAAI/bge-large-en-v1.5 (1024d) |
| **Chunk Size** | 800 characters |
| **Chunk Overlap** | 100 characters |
| **Vector DB** | ChromaDB (cosine space) |
| **BM25** | Okapi BM25 |
| **RRF Constant** | k=60 |
| **Vector Weight** | 60% |
| **Keyword Weight** | 40% |
| **Top-K Results** | 3 |
| **LLM Default** | phi4-mini:latest (Ollama) |

## 🔧 Troubleshooting

**Q: The frontend shows "Failed to connect to backend"**
```
# Ensure Django server is running
cd backend
python manage.py runserver 8000
```

**Q: Document processing fails with "no text could be extracted"**
```
# Check if the file is a scanned PDF (images, no text)
# Try OCR or use a text-based PDF
```

**Q: Ollama model not found**
```
# Pull the correct model name
ollama pull phi4-mini:latest
# Or update the settings.py default model name
```

**Q: ChromaDB errors**
```
# Delete and recreate the vector database
rm -rf backend/chroma_db_v2/
# Re-process your documents
```

**Q: "Add of existing embedding ID" errors**
```
# This was fixed by switching from add() to upsert()
# If you still see it, clear the chroma_db and re-process
```

## 📝 License

MIT License — Free for personal and commercial use.

## 🙏 Acknowledgments

- [ChromaDB](https://www.trychroma.com/) — Vector database
- [sentence-transformers](https://www.sbert.net/) — Embedding models
- [Ollama](https://ollama.ai/) — Local LLM inference
- [rank-bm25](https://github.com/dorianbrown/rank_bm25) — BM25 implementation
- [Django REST Framework](https://www.django-rest-framework.org/) — API framework