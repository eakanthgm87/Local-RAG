from django.urls import path

from . import views

urlpatterns = [
    # Health
    path('health/', views.health_check, name='health-check'),
    
    # Documents
    path('documents/', views.document_list, name='document-list'),
    path('documents/<uuid:pk>/', views.document_detail, name='document-detail'),
    path('documents/<uuid:pk>/process/', views.process_document, name='document-process'),
    path('documents/<uuid:pk>/download/', views.download_document, name='document-download'),
    
    # Chat Sessions
    path('sessions/', views.session_list, name='session-list'),
    path('sessions/<uuid:pk>/', views.session_detail, name='session-detail'),
    path('sessions/<uuid:pk>/messages/', views.session_messages, name='session-messages'),
    
    # Q&A
    path('ask/', views.ask_question, name='ask-question'),
    
    # Models
    path('models/ollama/', views.ollama_models, name='ollama-models'),
    path('models/groq/', views.groq_models, name='groq-models'),
    path('models/ollama/pull/', views.pull_ollama_model, name='ollama-pull'),
    
    # Status
    path('status/ollama/', views.ollama_status, name='ollama-status'),
    path('status/vector/', views.vector_status, name='vector-status'),
    
    # Logs
    path('logs/', views.query_logs, name='query-logs'),
]