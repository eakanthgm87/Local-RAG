"""
API Views for the Document Q&A System.
Endpoints:
- /api/health/ - Health check
- /api/documents/ - List/upload documents
- /api/documents/<id>/ - Document detail/delete
- /api/documents/<id>/process/ - Process document
- /api/ask/ - Ask a question
- /api/sessions/ - List/create chat sessions
- /api/sessions/<id>/ - Session detail/delete
- /api/sessions/<id>/messages/ - Session messages
- /api/models/ollama/ - List Ollama models
- /api/models/groq/ - List Groq models
- /api/status/ollama/ - Ollama server status
- /api/status/vector/ - Vector DB stats
"""
import os
import logging
import time
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, ChatSession, ChatMessage, QueryLog
from .serializers import (
    DocumentListSerializer,
    DocumentUploadSerializer,
    ChatSessionSerializer,
    ChatSessionListSerializer,
    ChatMessageSerializer,
    AskQuestionSerializer,
    QueryLogSerializer,
)
from .rag_pipeline import rag_pipeline
from .ollama_manager import ollama_manager
from .utils import get_file_type, get_file_size, guess_page_count

logger = logging.getLogger(__name__)


# ============================================================
# HEALTH CHECK
# ============================================================

@api_view(['GET'])
def health_check(request):
    """Health check endpoint."""
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0',
        'ollama_configured': settings.OLLAMA_BASE_URL is not None,
        'groq_configured': bool(settings.GROQ_API_KEY),
    })


# ============================================================
# DOCUMENT ENDPOINTS
# ============================================================

@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def document_list(request):
    """List all documents or upload a new one."""
    if request.method == 'GET':
        documents = Document.objects.all()
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = DocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            document = serializer.save()
            
            # Set file properties
            file_path = document.file.path
            document.file_size = get_file_size(file_path)
            document.file_type = get_file_type(document.file.name)
            document.save()
            
            return Response(
                DocumentListSerializer(document).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'DELETE'])
def document_detail(request, pk):
    """Get or delete a specific document."""
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = DocumentListSerializer(document)
        data = serializer.data
        # Add vector DB info
        try:
            chunk_count = rag_pipeline.vector_db.get_document_count(str(document.id))
            data['vector_chunks'] = chunk_count
        except Exception as e:
            data['vector_chunks'] = 0
        return Response(data)
    
    elif request.method == 'DELETE':
        # Delete from vector DB
        try:
            rag_pipeline.delete_document_chunks(str(document.id))
        except Exception as e:
            logger.warning(f"Failed to delete from vector DB: {e}")
        
        # Delete file
        if document.file and os.path.exists(document.file.path):
            os.remove(document.file.path)
        
        # Delete related sessions
        document.chat_sessions.all().delete()
        
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def process_document(request, pk):
    """Process a document: extract text, chunk, embed, and store in vector DB."""
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
    
    file_path = document.file.path
    
    try:
        if not os.path.exists(file_path):
            # File missing from disk - cleanup database record
            document.delete()
            return Response({'error': 'File not found on disk. Document record cleaned up.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        result = rag_pipeline.process_document(
            file_path=file_path,
            file_type=document.file_type,
            document_id=str(document.id)
        )
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        # Update document model
        document.processed = True
        document.chunk_count = result.get('chunk_count', 0)
        
        # Estimate page count from text if not set (with error handling)
        if document.page_count == 0:
            try:
                from .rag_pipeline import extract_text
                text = extract_text(file_path, document.file_type)
                document.page_count = guess_page_count(text, document.file_type)
            except Exception:
                document.page_count = 0  # Non-critical, skip this estimation
        
        document.save()
        
        return Response({
            **result,
            'title': document.title,
            'page_count': document.page_count,
        })
    
    except Exception as e:
        logger.error(f"Document processing failed: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def download_document(request, pk):
    """Download the original document file."""
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
    
    file_path = document.file.path
    if not os.path.exists(file_path):
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=document.file.name.split('/')[-1]
    )


# ============================================================
# CHAT SESSION ENDPOINTS
# ============================================================

@api_view(['GET', 'POST'])
def session_list(request):
    """List all chat sessions or create a new one."""
    if request.method == 'GET':
        sessions = ChatSession.objects.all()
        serializer = ChatSessionListSerializer(sessions, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        data = request.data
        title = data.get('title', 'New Chat')
        document_id = data.get('document_id')
        
        session = ChatSession.objects.create(
            title=title,
            document_id=document_id if document_id else None
        )
        
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
def session_detail(request, pk):
    """Get, update, or delete a chat session."""
    try:
        session = ChatSession.objects.get(pk=pk)
    except ChatSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        title = request.data.get('title')
        if title:
            session.title = title
            session.save()
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data)
    
    elif request.method == 'DELETE':
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
def session_messages(request, pk):
    """Get messages for a session or add a new message."""
    try:
        session = ChatSession.objects.get(pk=pk)
    except ChatSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        messages = session.messages.all()
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        data = request.data
        message = ChatMessage.objects.create(
            session=session,
            role=data.get('role', 'user'),
            content=data.get('content', ''),
        )
        
        # Update session title with first message
        if session.messages.count() == 1:
            session.title = data.get('content', 'New Chat')[:50]
            session.save()
        
        serializer = ChatMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ============================================================
# ASK QUESTION ENDPOINT
# ============================================================

@api_view(['POST'])
def ask_question(request):
    """
    Ask a question using the RAG pipeline.
    Expects: { question, session_id?, document_id?, llm_provider?, llm_model?, use_quantization? }
    """
    serializer = AskQuestionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    question = data['question']
    session_id = data.get('session_id')
    document_id = data.get('document_id')
    llm_provider = data.get('llm_provider', 'ollama')
    llm_model = data.get('llm_model', '')
    use_quantization = data.get('use_quantization', True)
    
    # Validate document exists
    if document_id:
        try:
            document = Document.objects.get(pk=document_id)
            if not document.processed:
                return Response({
                    'error': 'Document has not been processed yet. Please process it first.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Use the most recent processed document
        document = Document.objects.filter(processed=True).first()
        if not document:
            return Response({
                'error': 'No documents available. Please upload and process a document first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        document_id = str(document.id)
    
    # Run RAG pipeline
    start_time = time.time()
    result = rag_pipeline.ask_question(
        question=question,
        document_id=document_id,
        llm_provider=llm_provider,
        llm_model=llm_model,
        use_quantization=use_quantization,
    )
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    # Get or create session
    session = None
    if session_id:
        try:
            session = ChatSession.objects.get(pk=session_id)
        except ChatSession.DoesNotExist:
            pass
    
    if not session and document:
        # Create a new session automatically
        session = ChatSession.objects.create(
            title=question[:50],
            document=document,
        )
    
    # Save user message
    if session:
        ChatMessage.objects.create(
            session=session,
            role='user',
            content=question,
        )
        
        # Save assistant message with sources
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=result['answer'],
            sources=result.get('sources'),
        )
    
    # Log the query
    QueryLog.objects.create(
        document=document,
        session=session,
        question=question,
        answer=result['answer'],
        sources=result.get('sources'),
        llm_provider=llm_provider,
        llm_model=result.get('metadata', {}).get('llm_model', llm_model),
        latency_ms=elapsed_ms,
    )
    
    response_data = {
        **result,
        'session_id': str(session.id) if session else None,
    }
    
    return Response(response_data)


# ============================================================
# MODEL & STATUS ENDPOINTS
# ============================================================

@api_view(['GET'])
def ollama_models(request):
    """List available Ollama models."""
    models = rag_pipeline.get_ollama_models()
    
    # Add RAM requirement estimates for each model
    model_recommendations = {
        'phi4:mini': {'ram_gb': 2, 'description': 'Very fast, good for CPU, ~2GB RAM'},
        'phi4:14b': {'ram_gb': 8, 'description': 'Good quality, needs ~8GB RAM'},
        'llama3.2:3b': {'ram_gb': 3, 'description': 'Lightweight Llama, ~3GB RAM'},
        'llama3.2:1b': {'ram_gb': 1, 'description': 'Minimal, ~1GB RAM, fast'},
        'llama3.1:8b': {'ram_gb': 8, 'description': 'Good quality, ~8GB RAM'},
        'mistral:7b': {'ram_gb': 6, 'description': 'Popular choice, ~6GB RAM'},
        'gemma2:2b': {'ram_gb': 2, 'description': 'Google lightweight, ~2GB RAM'},
        'qwen2.5:0.5b': {'ram_gb': 0.5, 'description': 'Tiny model, <1GB RAM'},
        'qwen2.5:1.5b': {'ram_gb': 1.5, 'description': 'Small but capable, ~1.5GB RAM'},
        'qwen2.5:3b': {'ram_gb': 3, 'description': 'Balanced, ~3GB RAM'},
        'qwen2.5:7b': {'ram_gb': 6, 'description': 'Strong performance, ~6GB RAM'},
        'deepseek-r1:1.5b': {'ram_gb': 1.5, 'description': 'DeepSeek mini, ~1.5GB RAM'},
        'deepseek-r1:7b': {'ram_gb': 6, 'description': 'DeepSeek medium, ~6GB RAM'},
        'deepseek-r1:8b': {'ram_gb': 7, 'description': 'DeepSeek strong, ~7GB RAM'},
    }
    
    enhanced_models = []
    for m in models:
        model_name = m['name'].split(':')[0] + ':' + (m['name'].split(':')[1] if ':' in m['name'] else '')
        # Try to match with recommendations
        rec = model_recommendations.get(m['name']) or model_recommendations.get(model_name, {})
        m['ram_requirement_gb'] = rec.get('ram_gb', 'Unknown')
        m['description'] = rec.get('description', '')
        m['quantized'] = m.get('quantization_level', '') not in ['', 'N/A', None]
        enhanced_models.append(m)
    
    return Response({
        'models': enhanced_models,
        'count': len(enhanced_models),
    })


@api_view(['GET'])
def groq_models(request):
    """List available Groq models."""
    models = rag_pipeline.get_groq_models()
    return Response({
        'models': models,
        'count': len(models),
        'configured': rag_pipeline.groq.is_available(),
    })


@api_view(['POST'])
def pull_ollama_model(request):
    """Pull/download an Ollama model."""
    model_name = request.data.get('model')
    if not model_name:
        return Response({'error': 'Model name is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    success = rag_pipeline.ollama.pull_model(model_name)
    if success:
        return Response({'status': 'success', 'message': f'Model {model_name} pulled successfully'})
    else:
        return Response({'status': 'error', 'message': f'Failed to pull model {model_name}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST', 'DELETE'])
def ollama_status(request):
    """Check Ollama server status, or start/stop the server."""
    if request.method == 'GET':
        status_info = rag_pipeline.get_ollama_status()
        # Add installation info
        status_info['installed'] = ollama_manager.is_installed()
        # Add list of models currently loaded in memory
        if status_info.get('running'):
            status_info['running_models'] = ollama_manager.get_running_models()
        else:
            status_info['running_models'] = []
        return Response(status_info)
    
    elif request.method == 'POST':
        action = request.data.get('action', 'start')
        
        if action == 'start':
            result = ollama_manager.start_server()
            return Response(result)
        elif action == 'stop':
            result = ollama_manager.stop_server()
            return Response(result)
        elif action == 'run_model':
            model_name = request.data.get('model')
            if not model_name:
                return Response({'success': False, 'message': 'Model name required'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            result = ollama_manager.run_model(model_name)
            return Response(result)
        elif action == 'stop_model':
            model_name = request.data.get('model')
            if not model_name:
                return Response({'success': False, 'message': 'Model name required'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            result = ollama_manager.stop_model(model_name)
            return Response(result)
        elif action == 'remove_model':
            model_name = request.data.get('model')
            if not model_name:
                return Response({'success': False, 'message': 'Model name required'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            result = ollama_manager.remove_model(model_name)
            return Response(result)
        else:
            return Response({'success': False, 'message': f'Unknown action: {action}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        result = ollama_manager.stop_server()
        return Response(result)


@api_view(['GET'])
def vector_status(request):
    """Get vector database statistics."""
    stats = rag_pipeline.get_vector_stats()
    return Response(stats)


@api_view(['GET'])
def query_logs(request):
    """Get query logs for experiment tracking."""
    logs = QueryLog.objects.all()[:100]
    serializer = QueryLogSerializer(logs, many=True)
    return Response(serializer.data)