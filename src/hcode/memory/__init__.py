"""
HCODE Infinite Memory System

A three-layer persistent memory architecture:
- Layer 1: File-based memory (AGENT.md files)
- Layer 2: Session memory (conversation history with compression)
- Layer 3: Semantic memory (vector database for long-term retrieval)
"""

from .config import MemoryConfig, config, get_config, update_config
from .file_memory import FileMemory, MemoryFile
from .session_memory import SessionMemory, Session, Message, SessionSummary
from .embeddings import (
    EmbeddingModel,
    get_embedding_model,
    embed_text,
    embed_texts,
    cosine_similarity,
    get_embedding_model_safe,
    FallbackEmbedding,
)
from .semantic_memory import SemanticMemory, Memory, MemoryType
from .memory_manager import MemoryManager, ContextWindow, get_memory_manager

__all__ = [
    # Config
    "MemoryConfig",
    "config",
    "get_config",
    "update_config",
    # Layer 1: File Memory
    "FileMemory",
    "MemoryFile",
    # Layer 2: Session Memory
    "SessionMemory",
    "Session",
    "Message",
    "SessionSummary",
    # Embeddings
    "EmbeddingModel",
    "get_embedding_model",
    "embed_text",
    "embed_texts",
    "cosine_similarity",
    "get_embedding_model_safe",
    "FallbackEmbedding",
    # Layer 3: Semantic Memory
    "SemanticMemory",
    "Memory",
    "MemoryType",
    # Unified Manager
    "MemoryManager",
    "ContextWindow",
    "get_memory_manager",
]
