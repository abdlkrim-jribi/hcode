"""
Layer 3: Semantic memory using vector database.
Long‑term storage with similarity‑based retrieval.
Uses SQLite with optional sqlite‑vec extension.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
import json
import numpy as np
from enum import Enum

from hcode.memory.config import config
from hcode.memory.embeddings import get_embedding_model_safe, cosine_similarity


class MemoryType(Enum):
    """Types of memories that can be stored."""

    FACT = "fact"  # Factual information about the project/user
    PREFERENCE = "preference"  # User preferences and style
    CODE_PATTERN = "code_pattern"  # Code patterns and conventions
    DECISION = "decision"  # Architectural/design decisions
    CONTEXT = "context"  # General context about conversations
    ERROR = "error"  # Common errors and solutions
    TODO = "todo"  # Tasks and todos mentioned
    LEARNING = "learning"  # Things learned during sessions


@dataclass
class Memory:
    """Represents a single memory in the semantic store."""

    id: Optional[int] = None
    content: str = ""
    memory_type: MemoryType = MemoryType.CONTEXT
    source: str = ""  # Where this memory came from
    importance: float = 0.5  # 0‑1 importance score
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    project_id: Optional[str] = None  # For project‑specific memories

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "source": self.source,
            "importance": self.importance,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "project_id": self.project_id,
        }

    @classmethod
    def from_dict(cls, data: dict, embedding: Optional[np.ndarray] = None) -> "Memory":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            content=data["content"],
            memory_type=MemoryType(data.get("memory_type", "context")),
            source=data.get("source", ""),
            importance=data.get("importance", 0.5),
            embedding=embedding,
            metadata=data.get("metadata", {}),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
            last_accessed=(
                datetime.fromisoformat(data["last_accessed"])
                if "last_accessed" in data
                else datetime.now()
            ),
            access_count=data.get("access_count", 0),
            project_id=data.get("project_id"),
        )


# ---------------------------------------------------------------------------
# Vector‑based SemanticMemory implementation (the one used by the tests)
# ---------------------------------------------------------------------------


class SemanticMemory:
    """Vector database for semantic memory storage and retrieval.
    Uses SQLite with numpy for vector operations.
    """

    def __init__(self, db_path: Optional[Path] = None, project_id: Optional[str] = None):
        """Initialize semantic memory.

        Args:
            db_path: Path to SQLite database (default: ~/.hcode/memory.db)
            project_id: Optional project identifier for scoped queries.
        """
        self.db_path = db_path or config.db_path
        self.project_id = project_id
        self.embedding_model = get_embedding_model_safe()
        # Persistent connection used for the lifetime of the object.
        self._conn = sqlite3.connect(self.db_path)
        self._init_db()

    def close(self) -> None:
        """Close the persistent SQLite connection if it is open."""
        if hasattr(self, "_conn") and self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __del__(self):
        """Destructor to ensure the SQLite connection is closed."""
        self.close()

    def _init_db(self) -> None:
        """Initialize the database schema using the persistent connection."""
        conn = self._conn
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                source TEXT,
                importance REAL DEFAULT 0.5,
                embedding BLOB,
                metadata TEXT,
                created_at TEXT,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                project_id TEXT
            )
        """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_project_id ON memories(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        conn.commit()

    def _serialize_embedding(self, embedding: np.ndarray) -> bytes:
        """Convert numpy array to bytes for storage."""
        return embedding.astype(np.float32).tobytes()

    def _deserialize_embedding(self, data: bytes) -> np.ndarray:
        """Convert bytes back to numpy array."""
        return np.frombuffer(data, dtype=np.float32)

    def add(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.CONTEXT,
        source: str = "",
        importance: float = 0.5,
        metadata: Optional[Dict] = None,
        project_id: Optional[str] = None,
    ) -> Memory:
        """Add a new memory to the store.

        Args:
            content: The memory content
            memory_type: Type of memory
            source: Source of the memory (e.g., file, conversation)
            importance: Importance score (0‑1)
            metadata: Additional metadata
            project_id: Project identifier

        Returns:
            The created Memory object
        """
        embedding = self.embedding_model.embed(content)
        # Duplicate detection – simple similarity check
        if self._is_duplicate(content, embedding):
            existing = self._find_similar_memory(content, embedding)
            if existing:
                return self._update_memory_importance(existing, importance)

        mem = Memory(
            content=content,
            memory_type=memory_type,
            source=source,
            importance=importance,
            embedding=embedding,
            metadata=metadata or {},
            project_id=project_id or self.project_id,
        )
        conn = self._conn
        cursor = conn.execute(
            """
                INSERT INTO memories
                (content, memory_type, source, importance, embedding, metadata,
                 created_at, last_accessed, access_count, project_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mem.content,
                mem.memory_type.value,
                mem.source,
                mem.importance,
                self._serialize_embedding(embedding),
                json.dumps(mem.metadata),
                mem.created_at.isoformat(),
                mem.last_accessed.isoformat(),
                mem.access_count,
                mem.project_id,
            ),
        )
        mem.id = cursor.lastrowid
        conn.commit()
        return mem

    def _is_duplicate(self, content: str, embedding: np.ndarray, threshold: float = 0.95) -> bool:
        """Check if a similar memory already exists."""
        similar = self.search(content, top_k=1)
        return bool(similar and similar[0][1] >= threshold)

    def _find_similar_memory(self, content: str, embedding: np.ndarray) -> Optional[Memory]:
        """Find the most similar existing memory."""
        similar = self.search(content, top_k=1)
        return similar[0][0] if similar else None

    def _update_memory_importance(self, memory: Memory, new_importance: float) -> Memory:
        """Update a memory's importance (reinforcement)."""
        memory.importance = min(1.0, memory.importance + (new_importance * 0.1))
        memory.access_count += 1
        memory.last_accessed = datetime.now()
        conn = self._conn
        conn.execute(
            """
                UPDATE memories
                SET importance = ?, access_count = ?, last_accessed = ?
                WHERE id = ?
            """,
            (memory.importance, memory.access_count, memory.last_accessed.isoformat(), memory.id),
        )
        conn.commit()
        return memory

    def search(
        self,
        query: str,
        top_k: int = 10,
        memory_types: Optional[List[MemoryType]] = None,
        min_importance: float = 0.0,
        project_id: Optional[str] = None,
        include_global: bool = True,
    ) -> List[Tuple[Memory, float]]:
        """Search for relevant memories using semantic similarity.

        Args:
            query: Search query
            top_k: Maximum results to return
            memory_types: Filter by memory types
            min_importance: Minimum importance score
            project_id: Filter by project ID (None for all)
            include_global: Include global memories (project_id is None)
        """
        query_emb = self.embedding_model.embed(query)
        results: List[Tuple[Memory, float]] = []
        conn = self._conn
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM memories").fetchall()
        for row in rows:
            mem = Memory.from_dict(dict(row), self._deserialize_embedding(row["embedding"]))
            # Apply filters
            if memory_types and mem.memory_type not in memory_types:
                continue
            if mem.importance < min_importance:
                continue
            if project_id is not None:
                if mem.project_id != project_id:
                    continue
            elif not include_global and mem.project_id is None:
                continue
            sim = cosine_similarity(query_emb, mem.embedding)
            results.append((mem, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def prune(self, min_importance: float = 0.5) -> int:
        """Delete memories with importance below the threshold.

        Returns:
            Number of deleted records.
        """
        conn = self._conn
        cur = conn.execute("DELETE FROM memories WHERE importance < ?", (min_importance,))
        deleted = cur.rowcount
        conn.commit()
        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Return basic statistics about the memory store."""
        conn = self._conn
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        type_counts = conn.execute(
            "SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type"
        ).fetchall()
        return {
            "total_memories": total,
            "by_type": {row[0]: row[1] for row in type_counts},
        }
