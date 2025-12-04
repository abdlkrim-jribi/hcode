"""
Unified Memory Manager combining all three layers.
Provides a single interface for the agent to interact with memory.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from hcode.memory.config import MemoryConfig
from hcode.memory.file_memory import FileMemory
from hcode.memory.semantic_memory import SemanticMemory, Memory, MemoryType
from hcode.memory.session_memory import SessionMemory, Session


@dataclass
class ContextWindow:
    """Represents the assembled context for the agent."""

    file_memory: str  # From AGENT.md files
    session_summary: str  # Compressed history
    recent_messages: List[Dict[str, str]]  # Recent uncompressed messages
    semantic_context: str  # Retrieved relevant memories
    total_tokens: int  # Estimated token count
    metadata: Dict[str, Any]  # Additional info


class MemoryManager:
    """
    Unified interface for the three-layer memory system.

    Coordinates:
    - Layer 1: File memory (AGENT.md files)
    - Layer 2: Session memory (conversation persistence)
    - Layer 3: Semantic memory (vector database)
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        session_id: Optional[str] = None,
        config: Optional[MemoryConfig] = None,
    ):
        """
        Initialize the memory manager.

        Args:
            project_root: Project root directory
            session_id: Session identifier (auto-generated if not provided)
            config: Optional custom configuration
        """
        self.config = config or globals()["config"]
        self.project_root = project_root or Path.cwd()

        # Generate project ID from path
        self.project_id = self._generate_project_id(self.project_root)

        # Initialize all three layers
        self.file_memory = FileMemory(self.project_root)
        self.session_memory = SessionMemory(self.project_root)
        self.semantic_memory = SemanticMemory(project_id=self.project_id)

        # Load or create session
        if session_id:
            self.session = self.session_memory.load_session(session_id)
        else:
            self.session = self.session_memory.get_or_create_session()

    def _generate_project_id(self, path: Path) -> str:
        """Generate a unique project ID from path."""
        return hashlib.md5(str(path.resolve()).encode()).hexdigest()[:12]

    def add_message(
        self, role: str, content: str, is_anchor: bool = False, extract_memories: bool = True
    ) -> None:
        """
        Add a message to the conversation.

        Args:
            role: 'user' or 'assistant'
            content: Message content
            is_anchor: Mark as important (won't be compressed)
            extract_memories: Auto-extract facts to semantic memory
        """
        # Add to session memory
        message = self.session_memory.add_message(
            role=role,
            content=content,
            is_anchor=is_anchor,
            auto_anchor=True,  # Auto-detect important messages
        )

        # Extract and store memories periodically
        if extract_memories and self.config.extract_facts:
            message_count = len(self.session.messages)
            if message_count % self.config.extraction_interval == 0:
                self._extract_memories_from_recent()

    def _extract_memories_from_recent(self):
        """Extract facts and patterns from recent messages."""
        # Get recent messages for extraction
        recent = self.session.messages[-self.config.extraction_interval :]

        for msg in recent:
            content = msg.content

            # Extract facts (sentences with key patterns)
            facts = self._extract_facts(content)
            for fact in facts:
                self.semantic_memory.add(
                    content=fact,
                    memory_type=MemoryType.FACT,
                    source=f"session:{self.session.session_id}",
                    importance=0.6,
                )

            # Extract preferences
            if self.config.extract_preferences:
                preferences = self._extract_preferences(content)
                for pref in preferences:
                    self.semantic_memory.add(
                        content=pref,
                        memory_type=MemoryType.PREFERENCE,
                        source=f"session:{self.session.session_id}",
                        importance=0.7,
                    )

            # Extract code patterns
            if self.config.extract_code_patterns:
                patterns = self._extract_code_patterns(content)
                for pattern in patterns:
                    self.semantic_memory.add(
                        content=pattern,
                        memory_type=MemoryType.CODE_PATTERN,
                        source=f"session:{self.session.session_id}",
                        importance=0.5,
                    )

    def _extract_facts(self, content: str) -> List[str]:
        """Extract factual statements from content."""
        facts = []

        # Patterns indicating facts
        fact_patterns = [
            r"(?:is|are|was|were|uses?|requires?|depends? on)\s+.+",
            r"(?:the|this|our)\s+\w+\s+(?:is|are|uses?)\s+.+",
            r"(?:always|never|must|should)\s+.+",
        ]

        sentences = re.split(r"[.!?]\s+", content)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 200:
                continue

            for pattern in fact_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    facts.append(sentence)
                    break

        return facts[:5]  # Limit per message

    def _extract_preferences(self, content: str) -> List[str]:
        """Extract user preferences from content."""
        preferences = []

        # Patterns indicating preferences
        pref_patterns = [
            r"(?:I |we )(?:prefer|like|want|need|use)\s+.+",
            r"(?:please |always |never )(?:use|do|make)\s+.+",
            r"(?:my |our )(?:style|preference|convention)\s+.+",
        ]

        sentences = re.split(r"[.!?]\s+", content)
        for sentence in sentences:
            sentence = sentence.strip()
            for pattern in pref_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    preferences.append(sentence)
                    break

        return preferences[:3]

    def _extract_code_patterns(self, content: str) -> List[str]:
        """Extract code-related patterns and conventions."""
        patterns = []

        # Look for code conventions
        conv_patterns = [
            r"(?:naming convention|code style|format):\s*.+",
            r"(?:we use|using|prefer)\s+(?:camelCase|snake_case|PascalCase)",
            r"(?:tab|space|indent)\s*(?:size|width)?\s*(?:is|=|:)?\s*\d+",
        ]

        for pattern in conv_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            patterns.extend(matches)

        return patterns[:3]

    def get_context(
        self,
        query: Optional[str] = None,
        include_file_memory: bool = True,
        include_session: bool = True,
        include_semantic: bool = True,
        max_tokens: Optional[int] = None,
    ) -> ContextWindow:
        """
        Assemble context for the agent from all memory layers.

        Args:
            query: Optional query for semantic search
            include_file_memory: Include AGENT.md content
            include_session: Include session history
            include_semantic: Include semantic memory results
            max_tokens: Maximum context size

        Returns:
            ContextWindow with assembled context
        """
        max_tokens = max_tokens or self.config.max_context_tokens
        total_tokens = 0

        # Layer 1: File memory
        file_context = ""
        if include_file_memory:
            file_context = self.file_memory.get_combined_context()
            total_tokens += self._estimate_tokens(file_context)

        # Layer 2: Session memory
        session_summary = ""
        recent_messages = []
        if include_session:
            messages = self.session_memory.get_context_messages()

            # Split into summary and recent
            if self.session.summaries:
                summaries = [s.summary for s in self.session.summaries]
                session_summary = "\n\n".join(summaries)
                total_tokens += self._estimate_tokens(session_summary)

            recent_messages = messages
            for msg in recent_messages:
                total_tokens += self._estimate_tokens(msg.get("content", ""))

        # Layer 3: Semantic memory
        semantic_context = ""
        if include_semantic and query:
            results = self.semantic_memory.search(
                query=query,
                top_k=self.config.max_retrieval_results,
                project_id=self.project_id,
                include_global=True,
            )

            if results:
                memories = []
                for memory, score in results:
                    memories.append(f"- [{memory.memory_type.value}] {memory.content}")
                semantic_context = "## Relevant Memories\n" + "\n".join(memories)
                total_tokens += self._estimate_tokens(semantic_context)

        return ContextWindow(
            file_memory=file_context,
            session_summary=session_summary,
            recent_messages=recent_messages,
            semantic_context=semantic_context,
            total_tokens=total_tokens,
            metadata={
                "session_id": self.session.session_id,
                "project_id": self.project_id,
                "message_count": len(self.session.messages),
                "has_summaries": len(self.session.summaries) > 0,
            },
        )

    def build_system_context(self, query: Optional[str] = None) -> str:
        """
        Build complete system context string for injection.

        Args:
            query: Optional query for semantic retrieval

        Returns:
            Formatted context string
        """
        ctx = self.get_context(query=query)
        parts = []

        if ctx.file_memory:
            parts.append(f"<agent-memory>\n{ctx.file_memory}\n</agent-memory>")

        if ctx.session_summary:
            parts.append(f"<session-history>\n{ctx.session_summary}\n</session-history>")

        if ctx.semantic_context:
            parts.append(f"<semantic-memory>\n{ctx.semantic_context}\n</semantic-memory>")

        return "\n\n".join(parts)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token average)."""
        return len(text) // 4

    def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.CONTEXT,
        importance: float = 0.5,
        source: str = "user",
    ) -> Memory:
        """
        Explicitly add something to long-term memory.

        Args:
            content: What to remember
            memory_type: Type of memory
            importance: How important (0-1)
            source: Source of the memory

        Returns:
            The created Memory object
        """
        return self.semantic_memory.add(
            content=content,
            memory_type=memory_type,
            importance=importance,
            source=source,
            project_id=self.project_id,
        )

    def recall(
        self, query: str, top_k: int = 5, memory_types: Optional[List[MemoryType]] = None
    ) -> List[Tuple[Memory, float]]:
        """
        Search long-term memory for relevant information.

        Args:
            query: What to search for
            top_k: Number of results
            memory_types: Filter by types

        Returns:
            List of (Memory, similarity) tuples
        """
        return self.semantic_memory.search(
            query=query,
            top_k=top_k,
            memory_types=memory_types,
            project_id=self.project_id,
            include_global=True,
        )

    def forget(self, memory_id: int) -> bool:
        """Delete a specific memory."""
        return self.semantic_memory.forget(memory_id)

    def __del__(self):
        """Ensure semantic memory resources are released when the manager is garbage-collected."""
        try:
            self.semantic_memory.close()
        except Exception:
            pass

    def update_file_memory(
        self, content: str, scope: str = "project", section: Optional[str] = None
    ) -> Path:
        """
        Update an AGENT.md file.

        Args:
            content: Content to write
            scope: "global", "project", or "local"
            section: Optional section to update

        Returns:
            Path to updated file
        """
        return self.file_memory.update_memory(content=content, scope=scope, section=section)

    def mark_important(self, message_id: str) -> None:
        """Mark a message as important (anchor)."""
        self.session_memory.mark_anchor(message_id)

    def compact_session(self, target_messages: Optional[int] = None) -> None:
        """Manually trigger session compaction."""
        target = target_messages or self.config.max_recent_messages
        self.session_memory.compact(target_messages=target)

    def new_session(self) -> Session:
        """Start a new session (preserving history)."""
        self.session = self.session_memory.create_session()
        return self.session

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent sessions."""
        return self.session_memory.list_sessions(limit=limit)

    def switch_session(self, session_id: str) -> Session:
        """Switch to a different session."""
        self.session = self.session_memory.load_session(session_id)
        return self.session

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about all memory layers."""
        return {
            "project": {"root": str(self.project_root), "id": self.project_id},
            "file_memory": self.file_memory.get_memory_stats(),
            "session": {
                "id": self.session.session_id,
                "message_count": len(self.session.messages),
                "summary_count": len(self.session.summaries),
                "anchor_count": sum(1 for m in self.session.messages if m.is_anchor),
            },
            "semantic_memory": self.semantic_memory.get_stats(),
        }

    def cleanup(
        self, prune_semantic: bool = True, compact_session: bool = True, apply_decay: bool = True
    ) -> Dict[str, int]:
        """
        Perform cleanup on all memory layers.

        Args:
            prune_semantic: Remove low-importance memories
            compact_session: Compact session history
            apply_decay: Apply importance decay

        Returns:
            Cleanup statistics
        """
        stats = {}

        if prune_semantic:
            stats["memories_pruned"] = self.semantic_memory.prune(
                max_memories=self.config.max_memories,
                min_importance=self.config.min_importance_for_retention,
            )

        if apply_decay:
            self.semantic_memory.apply_importance_decay()
            stats["decay_applied"] = True

        if compact_session:
            original = len(self.session.messages)
            self.session_memory.compact(self.config.max_recent_messages)
            stats["messages_compacted"] = original - len(self.session.messages)

        return stats

    def export_all(self, output_dir: Path) -> Dict[str, Path]:
        """
        Export all memory data.

        Args:
            output_dir: Directory to export to

        Returns:
            Paths to exported files
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = {}

        # Export semantic memories
        semantic_path = output_dir / "semantic_memories.json"
        self.semantic_memory.export_memories(semantic_path, self.project_id)
        paths["semantic"] = semantic_path

        # Export session
        session_path = output_dir / f"session_{self.session.session_id}.json"
        self.session_memory.export_session(self.session.session_id, session_path)
        paths["session"] = session_path

        return paths

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save session."""
        self.session_memory.save_session()


def get_memory_manager(
    project_root: Optional[Path] = None, session_id: Optional[str] = None
) -> MemoryManager:
    """
    Convenience function to get a memory manager instance.

    Args:
        project_root: Project root directory
        session_id: Optional session ID to resume

    Returns:
        MemoryManager instance
    """
    return MemoryManager(project_root=project_root, session_id=session_id)
