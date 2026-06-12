"""
RAG Pipeline: Chunking, Embeddings, Hybrid Search (Vector + BM25), and LLM Inference.
"""
import os
import re
import time
import logging
import math
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter
import pickle

import numpy as np
import requests
import json

from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================
# TEXT EXTRACTION
# ============================================================

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file with page tracking."""
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text.strip():
            pages.append(f"[Page {i}]\n{text}")
    return "\n\n".join(pages)


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file."""
    from docx import Document
    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)
    return "\n\n".join(paragraphs)


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def extract_text(file_path: str, file_type: str) -> str:
    """Extract text from any supported file type."""
    if file_type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_type == 'docx':
        return extract_text_from_docx(file_path)
    elif file_type == 'txt':
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


# ============================================================
# CHUNKING STRATEGY (Improved)
# ============================================================

def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> List[Dict]:
    """
    Recursive character text splitting with semantic boundary awareness.
    
    Uses multiple split levels to maintain context integrity:
    1. Double newlines (paragraphs)
    2. Single newlines (lines)
    3. Sentence endings (. ! ?)
    4. Character-level fallback
    
    Args:
        text: Input text to chunk
        chunk_size: Target size of each chunk in characters (default: 800)
        chunk_overlap: Overlap between consecutive chunks in characters (default: 100)
        
    Returns:
        List of dicts with 'text', 'page' (if available), and 'chunk_index'
    """
    chunks = []
    
    # Pre-process: normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Split by double newlines first (paragraphs)
    paragraphs = text.split('\n\n')
    
    current_chunk = ""
    current_chunk_words = []
    page_num = None
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Track page numbers
        page_match = re.match(r'\[Page (\d+)\]', para)
        if page_match:
            page_num = int(page_match.group(1))
            # Remove the page marker from the text
            para = re.sub(r'\[Page \d+\]', '', para).strip()
            if not para:
                continue
        
        # If this single paragraph exceeds chunk_size, split it further
        if len(para) > chunk_size:
            # First save the current chunk if it exists
            if current_chunk.strip():
                chunks.append({
                    'text': current_chunk.strip(),
                    'page': page_num,
                    'chunk_index': len(chunks)
                })
                current_chunk = ""
                current_chunk_words = []
            
            # Split the long paragraph by sentences, then by character count
            sentences = re.split(r'(?<=[.!?])\s+', para)
            temp_chunk = ""
            for sent in sentences:
                if len(temp_chunk) + len(sent) > chunk_size and temp_chunk:
                    chunks.append({
                        'text': temp_chunk.strip(),
                        'page': page_num,
                        'chunk_index': len(chunks)
                    })
                    # Keep overlap
                    if chunk_overlap > 0:
                        overlap_start = max(0, len(temp_chunk) - chunk_overlap)
                        temp_chunk = temp_chunk[overlap_start:].strip()
                    else:
                        temp_chunk = ""
                temp_chunk += " " + sent if temp_chunk else sent
            
            if temp_chunk.strip():
                current_chunk = temp_chunk
        else:
            # If adding this paragraph exceeds chunk size, save current chunk
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    'text': current_chunk.strip(),
                    'page': page_num,
                    'chunk_index': len(chunks)
                })
                # Start new chunk with semantic overlap
                if chunk_overlap > 0 and current_chunk:
                    # Find a good boundary near the overlap point
                    overlap_start = max(0, len(current_chunk) - chunk_overlap)
                    overlap_text = current_chunk[overlap_start:]
                    
                    # Try sentence boundary first
                    last_period = overlap_text.rfind('. ')
                    last_newline = overlap_text.rfind('\n')
                    last_excl = overlap_text.rfind('! ')
                    last_q = overlap_text.rfind('? ')
                    split_point = max(last_period, last_newline, last_excl, last_q)
                    
                    if split_point > 0:
                        current_chunk = overlap_text[split_point+1:].strip()
                    else:
                        current_chunk = overlap_text.strip()
                else:
                    current_chunk = ""
                
                current_chunk += " " + para if current_chunk else para
            else:
                current_chunk += " " + para if current_chunk else para
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            'text': current_chunk.strip(),
            'page': page_num,
            'chunk_index': len(chunks)
        })
    
    return chunks


# ============================================================
# EMBEDDINGS (Sentence Transformers - bge-large-en-v1.5)
# ============================================================

class EmbeddingModel:
    """Singleton wrapper for the sentence-transformers embedding model."""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_model(self):
        """Load the embedding model (lazy loading)."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            logger.info("Embedding model loaded successfully")
        return self._model
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts into embeddings."""
        model = self.load_model()
        embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return embeddings
    
    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text string."""
        return self.encode([text])[0]


# ============================================================
# BM25 KEYWORD SEARCH (Hybrid)
# ============================================================

class BM25Index:
    """
    BM25 keyword search index for hybrid retrieval.
    Implements the Okapi BM25 algorithm for text retrieval.
    """
    
    _instance = None
    _bm25 = None
    _documents = None
    _doc_ids = None
    _document_id_map = None  # Maps document_id (from DB) -> list of chunk indices
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._bm25 is None:
            self._bm25 = None
            self._documents = []
            self._doc_ids = []
            self._document_id_map = {}
            self._corpus = {}  # chunk_id -> text
    
    def build_index(self, chunks: List[Dict], document_id: str):
        """
        Build or update BM25 index with new chunks.
        
        Args:
            chunks: List of chunk dicts with 'text' and 'chunk_index'
            document_id: The document ID these chunks belong to
        """
        from rank_bm25 import BM25Okapi
        
        # Tokenize and add new documents
        new_texts = [c['text'] for c in chunks]
        new_ids = [f"{document_id}_chunk_{c['chunk_index']}" for c in chunks]
        
        # Tokenize using simple whitespace + punctuation split
        tokenized = [self._tokenize(text) for text in new_texts]
        
        self._documents.extend(tokenized)
        self._doc_ids.extend(new_ids)
        
        # Store corpus mapping
        for idx, chunk in enumerate(chunks):
            self._corpus[new_ids[idx]] = chunk['text']
        
        # Track which chunks belong to which document
        if document_id not in self._document_id_map:
            self._document_id_map[document_id] = []
        self._document_id_map[document_id].extend(new_ids)
        
        # Rebuild the BM25 index
        if self._documents:
            self._bm25 = BM25Okapi(self._documents)
            logger.info(f"BM25 index rebuilt with {len(self._documents)} total chunks")
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words."""
        import re
        # Split on non-alphanumeric characters and lowercase
        tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        return tokens
    
    def search(self, query: str, top_k: int = 3, document_id: Optional[str] = None) -> List[Dict]:
        """
        Search using BM25 keyword matching.
        
        Args:
            query: The search query
            top_k: Number of results to return
            document_id: Optional document ID to filter by
            
        Returns:
            List of dicts with chunk info and BM25 scores
        """
        if self._bm25 is None or not self._documents:
            return []
        
        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []
        
        # Get scores for all documents
        scores = self._bm25.get_scores(tokenized_query)
        
        # Create results list with (score, index) tuples
        results = []
        for i, score in enumerate(scores):
            doc_id = self._doc_ids[i]
            
            # Filter by document_id if specified
            if document_id is not None:
                if not doc_id.startswith(f"{document_id}_chunk_"):
                    continue
            
            if score > 0:
                results.append({
                    'id': doc_id,
                    'text': self._corpus.get(doc_id, ''),
                    'score': float(score),
                    'chunk_index': i,
                })
        
        # Sort by BM25 score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:top_k]
    
    def delete_document(self, document_id: str):
        """Remove all chunks for a document from the BM25 index."""
        if document_id not in self._document_id_map:
            return
        
        chunk_ids_to_remove = set(self._document_id_map[document_id])
        
        # Filter out the removed chunks
        new_documents = []
        new_doc_ids = []
        for i, doc_id in enumerate(self._doc_ids):
            if doc_id not in chunk_ids_to_remove:
                new_documents.append(self._documents[i])
                new_doc_ids.append(doc_id)
        
        self._documents = new_documents
        self._doc_ids = new_doc_ids
        
        # Remove from corpus
        for chunk_id in chunk_ids_to_remove:
            self._corpus.pop(chunk_id, None)
        
        # Remove from document map
        del self._document_id_map[document_id]
        
        # Rebuild index
        if self._documents:
            from rank_bm25 import BM25Okapi
            self._bm25 = BM25Okapi(self._documents)
            logger.info(f"BM25 index rebuilt after deletion, {len(self._documents)} chunks remain")
        else:
            self._bm25 = None
            logger.info("BM25 index cleared (no documents remain)")
    
    def get_stats(self) -> Dict:
        """Get BM25 index statistics."""
        return {
            'total_chunks': len(self._documents),
            'total_documents': len(self._document_id_map),
            'method': 'BM25Okapi (keyword search)',
        }


# ============================================================
# VECTOR DATABASE (ChromaDB)
# ============================================================

class VectorDatabase:
    """Wrapper for ChromaDB vector database."""
    
    _instance = None
    _client = None
    _collection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def client(self):
        """Lazy load ChromaDB client."""
        if self._client is None:
            import chromadb
            persist_dir = settings.CHROMA_DB_PATH
            os.makedirs(persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=persist_dir)
            logger.info(f"ChromaDB client initialized at {persist_dir}")
        return self._client
    
    @property
    def collection(self):
        """Get or create the document chunks collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="document_chunks",
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection
    
    def add_chunks(self, document_id: str, chunks: List[Dict], embeddings: np.ndarray):
        """Add chunks with their embeddings to the vector store using upsert (replaces existing)."""
        ids = [f"{document_id}_chunk_{c['chunk_index']}" for c in chunks]
        documents = [c['text'] for c in chunks]
        # ChromaDB v1.5+ requires all metadata values to be str, int, float, or bool (not None)
        metadatas = []
        for c in chunks:
            meta = {
                'document_id': str(document_id),
                'chunk_index': int(c['chunk_index']),
            }
            page_val = c.get('page')
            if page_val is not None:
                meta['page'] = int(page_val)
            metadatas.append(meta)
        
        # Use upsert instead of add to handle re-processing (replaces existing chunks with same IDs)
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Upserted {len(chunks)} chunks for document {document_id}")
        return len(chunks)
    
    def search(self, query_embedding: np.ndarray, top_k: int = 3, document_id: Optional[str] = None) -> List[Dict]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query_embedding: The query embedding vector
            top_k: Number of results to return
            document_id: Optional document ID to filter by
            
        Returns:
            List of dicts with chunk info and similarity scores
        """
        where_filter = {"document_id": document_id} if document_id else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': 1 - results['distances'][0][i] if results['distances'] else 0.0,
                })
        
        return formatted_results
    
    def delete_document(self, document_id: str):
        """Delete all chunks for a given document."""
        self.collection.delete(
            where={"document_id": document_id}
        )
        logger.info(f"Deleted chunks for document {document_id}")
    
    def get_document_count(self, document_id: str) -> int:
        """Get the number of chunks for a document."""
        result = self.collection.get(
            where={"document_id": document_id}
        )
        return len(result['ids']) if result and 'ids' in result else 0
    
    def get_collection_stats(self) -> Dict:
        """Get collection statistics."""
        count = self.collection.count()
        return {
            'total_chunks': count,
            'collection_name': 'document_chunks',
        }


# ============================================================
# HYBRID SEARCH (Vector + BM25 Fusion)
# ============================================================

class HybridSearch:
    """
    Combines vector search (ChromaDB) with keyword search (BM25)
    using Reciprocal Rank Fusion (RRF) for optimal results.
    """
    
    def __init__(self):
        self.vector_db = VectorDatabase()
        self.bm25 = BM25Index()
        self.embedder = EmbeddingModel()
    
    def search(
        self,
        query: str,
        top_k: int = 3,
        document_id: Optional[str] = None,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ) -> List[Dict]:
        """
        Hybrid search combining vector similarity and keyword matching.
        
        Uses Reciprocal Rank Fusion (RRF) to merge results from:
        1. Vector search (semantic similarity via ChromDB)
        2. Keyword search (exact term matching via BM25)
        
        Args:
            query: The search query
            top_k: Number of final results to return
            document_id: Optional document ID to filter by
            vector_weight: Weight for vector search scores (0.0 - 1.0)
            keyword_weight: Weight for keyword search scores (0.0 - 1.0)
            
        Returns:
            List of dicts with merged and reranked results
        """
        if not query.strip():
            return []
        
        # Fetch more candidates from each method for better fusion
        candidates_per_method = max(top_k * 3, 10)
        
        # Step 1: Vector search
        query_embedding = self.embedder.encode_single(query)
        vector_results = self.vector_db.search(
            query_embedding,
            top_k=candidates_per_method,
            document_id=document_id
        )
        
        # Step 2: BM25 keyword search
        keyword_results = self.bm25.search(
            query,
            top_k=candidates_per_method,
            document_id=document_id
        )
        
        # Step 3: Reciprocal Rank Fusion (RRF)
        # RRF formula: score = 1 / (k + rank)
        # where k is a constant (typically 60) and rank is the position
        rrf_constant = 60.0
        fused_scores = {}
        
        # Process vector results
        for rank, result in enumerate(vector_results, 1):
            chunk_id = result['id']
            rrf_score = 1.0 / (rrf_constant + rank)
            fused_scores[chunk_id] = {
                'score': rrf_score * vector_weight,
                'text': result['text'],
                'metadata': result.get('metadata', {}),
                'vector_score': result['score'],
                'keyword_score': 0.0,
            }
        
        # Process BM25 results
        for rank, result in enumerate(keyword_results, 1):
            chunk_id = result['id']
            rrf_score = 1.0 / (rrf_constant + rank)
            
            if chunk_id in fused_scores:
                fused_scores[chunk_id]['score'] += rrf_score * keyword_weight
                fused_scores[chunk_id]['keyword_score'] = result['score']
            else:
                fused_scores[chunk_id] = {
                    'score': rrf_score * keyword_weight,
                    'text': result['text'],
                    'metadata': {'document_id': document_id} if document_id else {},
                    'vector_score': 0.0,
                    'keyword_score': result['score'],
                }
        
        # Sort by fused score descending
        sorted_results = sorted(
            fused_scores.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )
        
        # Format final results
        final_results = []
        for chunk_id, data in sorted_results[:top_k]:
            final_results.append({
                'id': chunk_id,
                'text': data['text'],
                'metadata': data['metadata'],
                'score': round(data['score'], 4),
                'vector_score': round(data['vector_score'], 4),
                'keyword_score': round(data['keyword_score'], 4),
                'method': 'hybrid',
            })
        
        return final_results
    
    def get_stats(self) -> Dict:
        """Get combined hybrid search statistics."""
        vector_stats = self.vector_db.get_collection_stats()
        bm25_stats = self.bm25.get_stats()
        return {
            'vector': vector_stats,
            'keyword': bm25_stats,
            'hybrid': {
                'method': 'Reciprocal Rank Fusion (RRF)',
                'vector_weight': 0.6,
                'keyword_weight': 0.4,
                'rrf_constant': 60,
            }
        }


# ============================================================
# LLM INFERENCE - Ollama (Local)
# ============================================================

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
    
    def list_models(self) -> List[Dict]:
        """List available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [
                    {
                        'name': m['name'],
                        'size': m.get('size', 0),
                        'modified_at': m.get('modified_at', ''),
                        'details': m.get('details', {}),
                        'quantization_level': m.get('details', {}).get('quantization_level', 'N/A'),
                    }
                    for m in models
                ]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
        return []
    
    def check_ollama_status(self) -> Dict:
        """Check if Ollama is running and get info."""
        try:
            response = requests.get(f"{self.base_url}/api/version", timeout=3)
            if response.status_code == 200:
                version_data = response.json()
                models = self.list_models()
                return {
                    'running': True,
                    'version': version_data.get('version', 'unknown'),
                    'models': models,
                    'model_count': len(models),
                }
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
        return {
            'running': False,
            'version': None,
            'models': [],
            'model_count': 0,
        }
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama."""
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=600  # Long timeout for model download
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
    
    def generate(self, prompt: str, model: str, options: Dict = None) -> str:
        """Generate a response using Ollama."""
        default_options = {
            "temperature": 0.0,
            "num_predict": 1024,
        }
        if options:
            default_options.update(options)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "options": default_options,
                    "stream": False,
                },
                timeout=120
            )
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                logger.error(f"Ollama generate failed: {response.status_code} - {response.text}")
                return f"Error: {response.status_code}"
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return f"Error: Could not reach Ollama. Is it running? ({str(e)})"
    
    def get_model_info(self, model_name: str) -> Dict:
        """Get detailed information about a specific model."""
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                details = data.get('details', {})
                return {
                    'name': model_name,
                    'license': data.get('license', '')[:200],
                    'modelfile': data.get('modelfile', '')[:500],
                    'parameters': data.get('parameters', ''),
                    'quantization': details.get('quantization_level', 'N/A'),
                    'family': details.get('family', ''),
                    'parameter_size': details.get('parameter_size', ''),
                }
        except Exception as e:
            logger.warning(f"Failed to get model info: {e}")
        return {'name': model_name}


# ============================================================
# LLM INFERENCE - Groq API (Cloud)
# ============================================================

class GroqClient:
    """Client for interacting with Groq API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.api_url = settings.GROQ_API_URL
    
    def is_available(self) -> bool:
        """Check if Groq API is configured."""
        return bool(self.api_key)
    
    def list_models(self) -> List[Dict]:
        """List available models from Groq."""
        if not self.is_available():
            return []
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                models = response.json().get('data', [])
                return [
                    {
                        'id': m['id'],
                        'created': m.get('created', 0),
                        'owned_by': m.get('owned_by', ''),
                        'context_window': m.get('context_window', 8192),
                    }
                    for m in models
                ]
        except Exception as e:
            logger.warning(f"Failed to list Groq models: {e}")
        return []
    
    def generate(self, prompt: str, model: str = None, system_prompt: str = None) -> str:
        """Generate a response using Groq API."""
        if not self.is_available():
            return "Groq API key not configured. Please set GROQ_API_KEY environment variable."
        
        model = model or settings.GROQ_MODEL
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": 1024,
            }
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                return f"Error: {response.json().get('error', {}).get('message', 'Unknown error')}"
        except Exception as e:
            logger.error(f"Groq request failed: {e}")
            return f"Error: Could not reach Groq API ({str(e)})"


# ============================================================
# MAIN RAG PIPELINE
# ============================================================

class RAGPipeline:
    """
    Main RAG pipeline orchestrating chunking, embeddings,
    hybrid retrieval (Vector + BM25), and LLM inference.
    """
    
    def __init__(self):
        self.embedder = EmbeddingModel()
        self.vector_db = VectorDatabase()
        self.hybrid_search = HybridSearch()
        self.bm25 = BM25Index()
        self.ollama = OllamaClient()
        self.groq = GroqClient()
    
    def process_document(self, file_path: str, file_type: str, document_id: str) -> Dict:
        """
        Process a document: extract text, chunk, embed, and store in vector DB + BM25 index.
        
        Returns:
            Dict with processing stats
        """
        start_time = time.time()
        
        # Step 1: Extract text
        text = extract_text(file_path, file_type)
        if not text.strip():
            return {'error': 'No text could be extracted from the document.'}
        
        # Step 2: Chunk the text (using improved chunking params)
        chunks = chunk_text(
            text,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        if not chunks:
            return {'error': 'No chunks could be created from the document.'}
        
        # Step 3: Generate embeddings
        texts = [c['text'] for c in chunks]
        embeddings = self.embedder.encode(texts)
        
        # Step 4: Store in vector DB (ChromaDB)
        chunk_count = self.vector_db.add_chunks(document_id, chunks, embeddings)
        
        # Step 5: Build BM25 keyword index
        self.bm25.build_index(chunks, document_id)
        
        elapsed = time.time() - start_time
        
        return {
            'document_id': str(document_id),
            'chunk_count': chunk_count,
            'total_characters': len(text),
            'processing_time_seconds': round(elapsed, 2),
            'retrieval_method': 'hybrid (ChromaDB + BM25)',
        }
    
    def ask_question(
        self,
        question: str,
        document_id: str,
        llm_provider: str = 'ollama',
        llm_model: str = '',
        use_quantization: bool = True,
        top_k: int = None
    ) -> Dict:
        """
        Answer a question using RAG pipeline with hybrid search.
        
        Args:
            question: The user's question
            document_id: ID of the document to query
            llm_provider: 'ollama' or 'groq'
            llm_model: Model name (empty for default)
            use_quantization: Whether to use quantized models (Ollama only)
            top_k: Number of chunks to retrieve
            
        Returns:
            Dict with answer, sources, and metadata
        """
        start_time = time.time()
        top_k = top_k or settings.TOP_K_RESULTS
        
        # Step 1: Hybrid search (Vector + BM25)
        results = self.hybrid_search.search(
            query=question,
            top_k=top_k,
            document_id=document_id
        )
        
        if not results:
            # Fallback to vector-only search
            logger.info("Hybrid search returned no results, falling back to vector search")
            query_embedding = self.embedder.encode_single(question)
            results = self.vector_db.search(
                query_embedding,
                top_k=top_k,
                document_id=document_id
            )
        
        if not results:
            return {
                'answer': 'No relevant context found in the document. Please upload a document first.',
                'sources': [],
                'metadata': {'chunks_retrieved': 0},
            }
        
        # Determine which retrieval method was used
        retrieval_method = 'hybrid'
        if 'vector_score' in results[0]:
            retrieval_method = 'hybrid (vector + keyword)'
        else:
            retrieval_method = 'vector-only'
        
        # Step 2: Build context from retrieved chunks
        context_parts = []
        sources = []
        for i, r in enumerate(results, 1):
            page_info = f" [Page {r['metadata'].get('page', 'N/A')}]" if r['metadata'].get('page') else ""
            context_parts.append(f"[Source {i}]{page_info}\n{r['text']}")
            source_entry = {
                'index': i,
                'text': r['text'][:200] + '...' if len(r['text']) > 200 else r['text'],
                'page': r['metadata'].get('page'),
                'score': round(r['score'], 4),
            }
            # Add hybrid search scores if available
            if 'vector_score' in r:
                source_entry['vector_score'] = round(r['vector_score'], 4)
            if 'keyword_score' in r:
                source_entry['keyword_score'] = round(r['keyword_score'], 4)
            sources.append(source_entry)
        
        context = "\n\n".join(context_parts)
        
        # Step 3: Build prompt with improved instructions
        prompt = f"""You are a document Q&A system. Answer using ONLY the context below.
If the answer is not present in the context, say "I don't know based on the provided context."
Cite sources with [Source X] when using specific information.

Context:
{context}

Question: {question}

Answer:"""
        
        # Step 4: Call LLM
        answer = self._call_llm(prompt, llm_provider, llm_model)
        
        elapsed = time.time() - start_time
        
        return {
            'answer': answer,
            'sources': sources,
            'metadata': {
                'chunks_retrieved': len(results),
                'llm_provider': llm_provider,
                'llm_model': llm_model or (settings.DEFAULT_OLLAMA_MODEL if llm_provider == 'ollama' else settings.GROQ_MODEL),
                'latency_ms': int(elapsed * 1000),
                'quantization': use_quantization,
                'retrieval_method': retrieval_method,
                'chunk_size': settings.CHUNK_SIZE,
                'chunk_overlap': settings.CHUNK_OVERLAP,
                'embedding_model': settings.EMBEDDING_MODEL_NAME,
            }
        }
    
    def _call_llm(self, prompt: str, provider: str, model: str) -> str:
        """Route the prompt to the appropriate LLM provider."""
        if provider == 'groq':
            if not self.groq.is_available():
                return "Groq API key not configured. Please set GROQ_API_KEY in environment variables."
            model_name = model or settings.GROQ_MODEL
            return self.groq.generate(prompt, model=model_name)
        else:
            # Default to Ollama
            model_name = model or settings.DEFAULT_OLLAMA_MODEL
            return self.ollama.generate(prompt, model=model_name)
    
    def get_ollama_models(self) -> List[Dict]:
        """Get list of available Ollama models with info."""
        return self.ollama.list_models()
    
    def get_ollama_status(self) -> Dict:
        """Get Ollama server status and model info."""
        return self.ollama.check_ollama_status()
    
    def get_groq_models(self) -> List[Dict]:
        """Get list of available Groq models."""
        return self.groq.list_models()
    
    def get_vector_stats(self) -> Dict:
        """Get combined retrieval statistics."""
        return self.hybrid_search.get_stats()
    
    def delete_document_chunks(self, document_id: str):
        """Delete all chunks for a document from both indexes."""
        self.vector_db.delete_document(document_id)
        self.bm25.delete_document(document_id)
        logger.info(f"Deleted all chunks for document {document_id} from both indexes")


# Singleton instance
rag_pipeline = RAGPipeline()