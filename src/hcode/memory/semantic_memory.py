"""
Layer 3: Semantic memory using vector database.
Long-term storage with similarity-based retrieval.
Uses SQLite with optional sqlite-vec extension.
"""
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
import json
import numpy as np
from enum import Enum

from .config import config
from .embeddings import get_embedding_model_safe, cosine_similarity


class MemoryType(Enum):
    """Types of memories that can be stored."""
    FACT = "fact"                  # Factual information about the project/user
    PREFERENCE = "preference"      # User preferences and style
    CODE_PATTERN = "code_pattern"  # Code patterns and conventions
    DECISION = "decision"          # Architectural/design decisions
    CONTEXT = "context"            # General context about conversations
    ERROR = "error"                # Common errors and solutions
    TODO = "todo"                  # Tasks and todos mentioned
    LEARNING = "learning"          # Things learned during sessions


@dataclass
class Memory:
    """Represents a single memory in the semantic store."""
    id: Optional[int] = None
    content: str = ""
    memory_type: MemoryType = MemoryType.CONTEXT
    source: str = ""              # Where this memory came from
    importance: float = 0.5       # 0-1 importance score
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    project_id: Optional[str] = None  # For project-specific memories

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
            "project_id": self.project_id
        }

    @classmethod
    def from_dict(cls, data: dict, embedding: Optional[np.ndarray] = None) -> 'Memory':
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            content=data["content"],
            memory_type=MemoryType(data.get("memory_type", "context")),
            source=data.get("source", ""),
            importance=data.get("importance", 0.5),
            embedding=embedding,
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if "last_accessed" in data else datetime.now(),
            access_count=data.get("access_count", 0),
            project_id=data.get("project_id")
        )


class SemanticMemory:
    """Semantic memory backed by a SQLite database.

    The original implementation kept a persistent ``sqlite3.Connection``
    open for the lifetime of the object.  In the test suite a temporary
    directory is created for each test and the ``SemanticMemory`` instance
    is discarded at the end of the test.  Windows does not allow a file to be
    removed while it is still opened, which caused ``PermissionError``
    during the fixture teardown.

    To fix this we:
    * Store the connection in ``self._conn`` and open it lazily.
    * Provide a ``close()`` method that explicitly closes the connection.
    * Call ``self.close()`` at the start of ``clear()`` and in ``__del__``
      to guarantee the file handle is released before the directory is
      removed.
    * Guard all database operations with ``self._ensure_connection()``
      which (re)opens the connection if it was closed.
    """
    def __init__(self, storage_path: Path | str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_path / "semantic.db"
        self._conn: sqlite3.Connection | None = None
        self._ensure_connection()
        self._create_table()

    def _ensure_connection(self) -> None:
        """Open a SQLite connection if one is not already open."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)

    def _create_table(self) -> None:
        self._ensure_connection()
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS memories (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )"""
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying SQLite connection if it is open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def clear(self) -> None:
        """Delete all records and the underlying database file.
        The connection is closed first to avoid file‑locking issues on
        Windows.
        """
        self.close()
        if self.db_path.exists():
            self.db_path.unlink()
        # Re‑create an empty database for further use
        self._ensure_connection()
        self._create_table()

    # Existing public API -------------------------------------------------
    def store(self, key: str, value: str) -> None:
        self._ensure_connection()
        self._conn.execute(
            "INSERT OR REPLACE INTO memories (key, value) VALUES (?, ?)",
            (key, value),
        )
        self._conn.commit()

    def retrieve(self, key: str) -> str | None:
        self._ensure_connection()
        cur = self._conn.execute(
            "SELECT value FROM memories WHERE key = ?", (key,)
        )
        row = cur.fetchone()
        return row[0] if row else None

    def delete(self, key: str) -> None:
        self._ensure_connection()
        self._conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        self._conn.commit()

    def __del__(self) -> None:
        # Ensure the connection is closed when the object is garbage‑collected
        # Use hasattr to guard against missing _conn attribute
        if hasattr(self, '_conn') and self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass

    """
    Vector database for semantic memory storage and retrieval.
    Uses SQLite with numpy for vector operations.
    """

    def __init__(self, db_path: Optional[Path] = None, project_id: Optional[str] = None):
        """
        Initialize semantic memory.

        Args:
            db_path: Path to SQLite database (default: ~/.hcode/memory.db)
            project_id: Optional project identifier for scoped queries
        """
        self.db_path = db_path or config.db_path
        self.project_id = project_id
        self.embedding_model = get_embedding_model_safe()
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
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
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_id ON memories(project_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)
            """)
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
        project_id: Optional[str] = None
    ) -> Memory:
        """
        Add a new memory to the store.

        Args:
            content: The memory content
            memory_type: Type of memory
            source: Source of the memory (e.g., file, conversation)
            importance: Importance score (0-1)
            metadata: Additional metadata
            project_id: Project identifier

        Returns:
            The created Memory object
        """
        # Generate embedding
        embedding = self.embedding_model.embed(content)

        # Check for duplicates
        if self._is_duplicate(content, embedding):
            # Update existing instead
            existing = self._find_similar_memory(content, embedding)
            if existing:
                return self._update_memory_importance(existing, importance)

        memory = Memory(
            content=content,
            memory_type=memory_type,
            source=source,
            importance=importance,
            embedding=embedding,
            metadata=metadata or {},
            project_id=project_id or self.project_id
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO memories
                (content, memory_type, source, importance, embedding, metadata,
                 created_at, last_accessed, access_count, project_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.content,
                memory.memory_type.value,
                memory.source,
                memory.importance,
                self._serialize_embedding(embedding),
                json.dumps(memory.metadata),
                memory.created_at.isoformat(),
                memory.last_accessed.isoformat(),
                memory.access_count,
                memory.project_id
            ))
            memory.id = cursor.lastrowid
            conn.commit()

        return memory

    def _is_duplicate(self, content: str, embedding: np.ndarray, threshold: float = 0.95) -> bool:
        """Check if a similar memory already exists."""
        similar = self.search(content, top_k=1)
        if similar and similar[0][1] >= threshold:
            return True
        return False

    def _find_similar_memory(self, content: str, embedding: np.ndarray) -> Optional[Memory]:
        """Find the most similar existing memory."""
        similar = self.search(content, top_k=1)
        if similar:
            return similar[0][0]
        return None

    def _update_memory_importance(self, memory: Memory, new_importance: float) -> Memory:
        """Update a memory's importance (reinforcement)."""
        # Increase importance when seen again
        memory.importance = min(1.0, memory.importance + (new_importance * 0.1))
        memory.access_count += 1
        memory.last_accessed = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE memories
                SET importance = ?, access_count = ?, last_accessed = ?
                WHERE id = ?
            """, (memory.importance, memory.access_count,
                  memory.last_accessed.isoformat(), memory.id))
            conn.commit()

        return memory

    def search(
        self,
        query: str,
        top_k: int = 10,
        memory_types: Optional[List[MemoryType]] = None,
        min_importance: float = 0.0,
        project_id: Optional[str] = None,
        include_global: bool = True
    ) -> List[Tuple[Memory, float]]:
        """
        Search for relevant memories using semantic similarity.

        Args:
            query: Search query
            top_k: Maximum results to return
            memory_types: Filter by memory types
            min_importance: Minimum importance threshold
            project_id: Filter by project
            include_global: Include memories without project_id

        Returns:
            List of (Memory, similarity_score) tuples
        """
        # Generate query embedding
        query_embedding = self.embedding_model.embed(query)

        # Build SQL query
        conditions = ["importance >= ?"]
        params = [min_importance]

        if memory_types:
            placeholders = ",".join("?" * len(memory_types))
            conditions.append(f"memory_type IN ({placeholders})")
            params.extend(mt.value for mt in memory_types)

        # Project filtering
        project_id = project_id or self.project_id
        if project_id:
            if include_global:
                conditions.append("(project_id = ? OR project_id IS NULL)")
            else:
                conditions.append("project_id = ?")
            params.append(project_id)

        where_clause = " AND ".join(conditions)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT id, content, memory_type, source, importance, embedding,
                       metadata, created_at, last_accessed, access_count, project_id
                FROM memories
                WHERE {where_clause}
            """, params)

            results = []
            for row in cursor:
                embedding = self._deserialize_embedding(row[5])
                similarity = cosine_similarity(query_embedding, embedding)

                if similarity >= config.min_similarity_threshold:
                    memory = Memory(
                        id=row[0],
                        content=row[1],
                        memory_type=MemoryType(row[2]),
                        source=row[3],
                        importance=row[4],
                        embedding=embedding,
                        metadata=json.loads(row[6]) if row[6] else {},
                        created_at=datetime.fromisoformat(row[7]),
                        last_accessed=datetime.fromisoformat(row[8]),
                        access_count=row[9],
                        project_id=row[10]
                    )
                    results.append((memory, similarity))

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x[1], reverse=True)
        top_results = results[:top_k]

        # Update access timestamps for retrieved memories
        self._update_access(top_results)

        return top_results

    def _update_access(self, results: List[Tuple[Memory, float]]):
        """Update access timestamps for retrieved memories."""
        if not results:
            return

        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            for memory, _ in results:
                conn.execute("""
                    UPDATE memories
                    SET last_accessed = ?, access_count = access_count + 1
                    WHERE id = ?
                """, (now, memory.id))
            conn.commit()

    def get_by_type(
        self,
        memory_type: MemoryType,
        limit: int = 50,
        project_id: Optional[str] = None
    ) -> List[Memory]:
        """
        Get memories of a specific type.

        Args:
            memory_type: Type of memories to retrieve
            limit: Maximum number to return
            project_id: Filter by project

        Returns:
            List of Memory objects
        """
        project_id = project_id or self.project_id

        with sqlite3.connect(self.db_path) as conn:
            if project_id:
                cursor = conn.execute("""
                    SELECT id, content, memory_type, source, importance, embedding,
                           metadata, created_at, last_accessed, access_count, project_id
                    FROM memories
                    WHERE memory_type = ? AND (project_id = ? OR project_id IS NULL)
                    ORDER BY importance DESC, last_accessed DESC
                    LIMIT ?
                """, (memory_type.value, project_id, limit))
            else:
                cursor = conn.execute("""
                    SELECT id, content, memory_type, source, importance, embedding,
                           metadata, created_at, last_accessed, access_count, project_id
                    FROM memories
                    WHERE memory_type = ?
                    ORDER BY importance DESC, last_accessed DESC
                    LIMIT ?
                """, (memory_type.value, limit))

            return [
                Memory(
                    id=row[0],
                    content=row[1],
                    memory_type=MemoryType(row[2]),
                    source=row[3],
                    importance=row[4],
                    embedding=self._deserialize_embedding(row[5]) if row[5] else None,
                    metadata=json.loads(row[6]) if row[6] else {},
                    created_at=datetime.fromisoformat(row[7]),
                    last_accessed=datetime.fromisoformat(row[8]),
                    access_count=row[9],
                    project_id=row[10]
                )
                for row in cursor
            ]

    def delete(self, memory_id: int) -> bool:
        """Delete a memory by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_importance(self, memory_id: int, importance: float) -> bool:
        """Update a memory's importance score."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE memories SET importance = ? WHERE id = ?",
                (importance, memory_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def prune(
        self,
        max_memories: Optional[int] = None,
        min_importance: Optional[float] = None,
        older_than_days: Optional[int] = None
    ) -> int:
        """
        Prune old or low-importance memories.

        Args:
            max_memories: Maximum memories to keep (keeps most important)
            min_importance: Delete memories below this importance
            older_than_days: Delete memories older than this

        Returns:
            Number of memories deleted
        """
        deleted = 0

        with sqlite3.connect(self.db_path) as conn:
            # Delete by importance threshold
            if min_importance is not None:
                cursor = conn.execute(
                    "DELETE FROM memories WHERE importance < ?",
                    (min_importance,)
                )
                deleted += cursor.rowcount

            # Delete by age
            if older_than_days is not None:
                from datetime import timedelta
                cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                cursor = conn.execute(
                    "DELETE FROM memories WHERE last_accessed < ? AND importance < 0.8",
                    (cutoff,)
                )
                deleted += cursor.rowcount

            # Enforce max memories limit
            if max_memories is not None:
                cursor = conn.execute("SELECT COUNT(*) FROM memories")
                count = cursor.fetchone()[0]

                if count > max_memories:
                    to_delete = count - max_memories
                    cursor = conn.execute("""
                        DELETE FROM memories WHERE id IN (
                            SELECT id FROM memories
                            ORDER BY importance ASC, last_accessed ASC
                            LIMIT ?
                        )
                    """, (to_delete,))
                    deleted += cursor.rowcount

            conn.commit()

        return deleted

    def apply_importance_decay(self, decay_rate: Optional[float] = None):
        """
        Apply time-based decay to importance scores.
        Memories accessed recently decay less.
        """
        decay_rate = decay_rate or config.importance_decay_rate

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, importance, last_accessed FROM memories
            """)

            now = datetime.now()
            updates = []

            for row in cursor:
                memory_id, importance, last_accessed = row
                last_access = datetime.fromisoformat(last_accessed)
                days_since_access = (now - last_access).days

                # Apply decay based on days since access
                decay = decay_rate * days_since_access
                new_importance = max(0.1, importance - decay)  # Minimum 0.1

                if new_importance != importance:
                    updates.append((new_importance, memory_id))

            # Batch update
            conn.executemany(
                "UPDATE memories SET importance = ? WHERE id = ?",
                updates
            )
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM memories")
            total = cursor.fetchone()[0]

            cursor = conn.execute("""
                SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type
            """)
            by_type = {row[0]: row[1] for row in cursor}

            cursor = conn.execute("SELECT AVG(importance) FROM memories")
            avg_importance = cursor.fetchone()[0] or 0

            cursor = conn.execute("SELECT SUM(access_count) FROM memories")
            total_accesses = cursor.fetchone()[0] or 0

        return {
            "total_memories": total,
            "by_type": by_type,
            "average_importance": round(avg_importance, 3),
            "total_accesses": total_accesses,
            "db_path": str(self.db_path)
        }

    def export_memories(self, output_path: Path, project_id: Optional[str] = None) -> int:
        """Export memories to JSON file."""
        project_id = project_id or self.project_id

        with sqlite3.connect(self.db_path) as conn:
            if project_id:
                cursor = conn.execute("""
                    SELECT id, content, memory_type, source, importance,
                           metadata, created_at, last_accessed, access_count, project_id
                    FROM memories
                    WHERE project_id = ? OR project_id IS NULL
                """, (project_id,))
            else:
                cursor = conn.execute("""
                    SELECT id, content, memory_type, source, importance,
                           metadata, created_at, last_accessed, access_count, project_id
                    FROM memories
                """)

            memories = []
            for row in cursor:
                memories.append({
                    "id": row[0],
                    "content": row[1],
                    "memory_type": row[2],
                    "source": row[3],
                    "importance": row[4],
                    "metadata": json.loads(row[5]) if row[5] else {},
                    "created_at": row[6],
                    "last_accessed": row[7],
                    "access_count": row[8],
                    "project_id": row[9]
                })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(memories, f, indent=2)

        return len(memories)

    def import_memories(self, input_path: Path) -> int:
        """Import memories from JSON file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            memories = json.load(f)

        count = 0
        for mem_data in memories:
            self.add(
                content=mem_data["content"],
                memory_type=MemoryType(mem_data.get("memory_type", "context")),
                source=mem_data.get("source", "import"),
                importance=mem_data.get("importance", 0.5),
                metadata=mem_data.get("metadata", {}),
                project_id=mem_data.get("project_id")
            )
            count += 1

        return count
