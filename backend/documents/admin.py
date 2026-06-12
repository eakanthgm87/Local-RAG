from django.contrib import admin
from .models import Document, ChatSession, ChatMessage, QueryLog


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'file_type', 'file_size', 'page_count', 'processed', 'chunk_count', 'uploaded_at']
    list_filter = ['file_type', 'processed']
    search_fields = ['title']
    readonly_fields = ['id', 'file_size', 'file_type', 'uploaded_at', 'chunk_count']


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'document', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['title']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'content_short', 'created_at']
    list_filter = ['role', 'created_at']
    
    def content_short(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_short.short_description = 'Content'


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ['question_short', 'llm_provider', 'llm_model', 'latency_ms', 'created_at']
    list_filter = ['llm_provider', 'created_at']
    
    def question_short(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question
    question_short.short_description = 'Question'