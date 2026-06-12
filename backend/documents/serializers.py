from rest_framework import serializers
from .models import Document, ChatSession, ChatMessage, QueryLog


class DocumentListSerializer(serializers.ModelSerializer):
    """Serializer for listing documents."""
    
    class Meta:
        model = Document
        fields = ['id', 'title', 'file_type', 'file_size', 'page_count', 
                  'uploaded_at', 'processed', 'chunk_count']


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading documents."""
    
    class Meta:
        model = Document
        fields = ['id', 'title', 'file', 'file_type', 'file_size', 'uploaded_at']
        read_only_fields = ['id', 'file_type', 'file_size', 'uploaded_at']

    def validate_file(self, value):
        """Validate file type and size."""
        allowed_types = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
        max_size = 50 * 1024 * 1024  # 50MB
        
        if value.content_type not in allowed_types:
            # Try to validate by extension
            ext = value.name.split('.')[-1].lower()
            if ext not in ['pdf', 'docx', 'txt']:
                raise serializers.ValidationError("Only PDF, DOCX, and TXT files are allowed.")
        
        if value.size > max_size:
            raise serializers.ValidationError("File size must be under 50MB.")
        
        return value


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'session', 'role', 'content', 'sources', 'created_at']
        read_only_fields = ['id', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for chat sessions."""
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'document', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChatSessionListSerializer(serializers.ModelSerializer):
    """Serializer for listing chat sessions."""
    document_title = serializers.CharField(source='document.title', read_only=True, default=None)
    
    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'document', 'document_title', 'created_at', 'updated_at']


class AskQuestionSerializer(serializers.Serializer):
    """Serializer for asking a question."""
    question = serializers.CharField(required=True, max_length=5000)
    session_id = serializers.CharField(required=False, allow_null=True)
    document_id = serializers.CharField(required=False, allow_null=True)
    llm_provider = serializers.ChoiceField(choices=['ollama', 'groq'], default='ollama')
    llm_model = serializers.CharField(required=False, allow_blank=True, default='')
    use_quantization = serializers.BooleanField(default=True)


class QueryLogSerializer(serializers.ModelSerializer):
    """Serializer for query logs."""
    
    class Meta:
        model = QueryLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']