"""
Layer 2: Session memory with persistence and compression.
Handles conversation history across sessions with intelligent summarization.

Features:
- Persistent storage across CLI invocations
- Automatic summarization when context grows too large
- Anchor messages that are never summarized
- Session continuation with --continue flag
"""

import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable

from hcode.memory.config import config


@dataclass
class Message:
    """A single conversation message."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    is_anchor: bool = False  # Important messages to preserve
    token_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SessionSummary:
    """Compressed representation of older conversation segments."""

    summary: str
    message_range: tuple  # (start_id, end_id)
    original_count: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    key_decisions: List[str] = field(default_factory=list)
    code_changes: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSummary":
        """Create from dictionary."""
        # Handle tuple conversion
        if isinstance(data.get("message_range"), list):
            data["message_range"] = tuple(data["message_range"])
        return cls(**data)


@dataclass
class Session:
    """A conversation session with full state."""

    session_id: str
    project_path: Optional[str]
    created_at: str
    updated_at: str
    messages: List[Message]
    summaries: List[SessionSummary]
    anchors: List[str]  # Message IDs marked as important
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "project_path": self.project_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
            "summaries": [s.to_dict() for s in self.summaries],
            "anchors": self.anchors,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            project_path=data.get("project_path"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            summaries=[SessionSummary.from_dict(s) for s in data.get("summaries", [])],
            anchors=data.get("anchors", []),
            metadata=data.get("metadata", {}),
        )


class SessionMemory:
    """
    Manages conversation sessions with automatic compression.

    Features:
    - Persistent storage across CLI invocations
    - Automatic summarization when context grows too large
    - Anchor messages that are never summarized
    - Session continuation with --continue flag
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        project_path: Optional[Path] = None,
        summarizer: Optional[Callable[[List[Message]], str]] = None,
    ):
        """
        Initialize session memory.

        Args:
            session_id: Specific session to load, or None for new/continue
            project_path: Project path for session association
            summarizer: Optional function to summarize messages (LLM-based)
        """
        self.sessions_dir = config.sessions_path
        self.sessions_dir.mkdir(exist_ok=True)

        self.project_path = project_path
        self.summarizer = summarizer or self._default_summarizer

        if session_id == "continue":
            # Find most recent session for this project
            self.session = self._find_recent_session() or self._create_session()
        elif session_id:
            self.session = self._load_session(session_id)
        else:
            self.session = self._create_session()

    def _session_file(self, session_id: str) -> Path:
        """Get path to session file."""
        return self.sessions_dir / f"{session_id}.json"

    def _create_session(self) -> Session:
        """Create a new session."""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]

        return Session(
            session_id=session_id,
            project_path=str(self.project_path) if self.project_path else None,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            messages=[],
            summaries=[],
            anchors=[],
            metadata={},
        )

    def _load_session(self, session_id: str) -> Session:
        """Load an existing session or create new if not found."""
        file_path = self._session_file(session_id)

        if not file_path.exists():
            # Try to find most recent session for this project
            session = self._find_recent_session()
            if session:
                return session
            return self._create_session()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Session.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            # Corrupted session file, create new
            return self._create_session()

    def _find_recent_session(self) -> Optional[Session]:
        """Find most recent session for current project."""
        sessions = []

        for file in self.sessions_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Filter by project if specified
                if self.project_path:
                    if data.get("project_path") != str(self.project_path):
                        continue

                sessions.append((data["updated_at"], file.stem, data))
            except (json.JSONDecodeError, KeyError):
                continue

        if sessions:
            sessions.sort(reverse=True)
            return Session.from_dict(sessions[0][2])

        return None

    def save(self):
        """Persist session to disk."""
        self.session.updated_at = datetime.now().isoformat()
        file_path = self._session_file(self.session.session_id)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.session.to_dict(), f, indent=2, ensure_ascii=False)

    def add_message(
        self, role: str, content: str, is_anchor: bool = False, auto_anchor: bool = True, **metadata
    ) -> Message:
        """
        Add a message to the session.

        Args:
            role: Message role (user, assistant, system, tool)
            content: Message content
            is_anchor: Explicitly mark as anchor
            auto_anchor: Auto-detect important messages
            **metadata: Additional metadata

        Returns:
            The created Message
        """
        # Auto-detect anchors based on keywords
        if auto_anchor and not is_anchor:
            is_anchor = self._should_anchor(content)

        message = Message(role=role, content=content, is_anchor=is_anchor, metadata=metadata)

        self.session.messages.append(message)

        if is_anchor:
            self.session.anchors.append(message.message_id)

        # Check if compression is needed
        if len(self.session.messages) > config.compression_threshold:
            self._trigger_compression()

        self.save()
        return message

    def _should_anchor(self, content: str) -> bool:
        """Determine if message should be auto-anchored."""
        content_lower = content.lower()
        return any(kw in content_lower for kw in config.anchor_keywords)

    def mark_anchor(self, message_id: str):
        """Mark a message as an anchor (preserved during compression)."""
        if message_id not in self.session.anchors:
            self.session.anchors.append(message_id)
            for msg in self.session.messages:
                if msg.message_id == message_id:
                    msg.is_anchor = True
                    break
            self.save()

    def unmark_anchor(self, message_id: str):
        """Remove anchor status from a message."""
        if message_id in self.session.anchors:
            self.session.anchors.remove(message_id)
            for msg in self.session.messages:
                if msg.message_id == message_id:
                    msg.is_anchor = False
                    break
            self.save()

    def _trigger_compression(self):
        """
        Compress older messages into summaries.
        Preserves recent messages and anchor messages.
        """
        recent_count = config.max_recent_messages

        if len(self.session.messages) <= recent_count:
            return

        # Split into old and recent
        to_compress = self.session.messages[:-recent_count]
        to_keep = self.session.messages[-recent_count:]

        # Extract anchors from compression candidates
        anchors_to_preserve = [m for m in to_compress if m.is_anchor]
        non_anchor_to_compress = [m for m in to_compress if not m.is_anchor]

        if non_anchor_to_compress:
            # Create summary
            summary = self._create_summary(non_anchor_to_compress)
            self.session.summaries.append(summary)

        # Update messages: anchors + recent
        self.session.messages = anchors_to_preserve + to_keep

    def _create_summary(self, messages: List[Message]) -> SessionSummary:
        """
        Create a summary of messages.
        Uses provided summarizer or default.
        """
        summary_text = self.summarizer(messages)

        return SessionSummary(
            summary=summary_text,
            message_range=(messages[0].message_id, messages[-1].message_id),
            original_count=len(messages),
            key_decisions=self._extract_decisions(messages),
            code_changes=self._extract_code_changes(messages),
            topics=self._extract_topics(messages),
        )

    def _default_summarizer(self, messages: List[Message]) -> str:
        """
        Default summarizer - creates a basic summary.
        Replace with LLM-based summarization for better results.
        """
        # Basic summary by extracting key information
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]

        summary_parts = []

        # Summarize user intents
        if user_messages:
            user_preview = "\n".join([f"- User: {m.content[:100]}..." for m in user_messages[:3]])
            summary_parts.append(f"User requests:\n{user_preview}")

        # Summarize assistant actions
        if assistant_messages:
            # Look for tool usage and key actions
            actions = []
            for m in assistant_messages:
                if "```" in m.content:
                    actions.append("- Provided code")
                if "created" in m.content.lower() or "wrote" in m.content.lower():
                    actions.append("- Created/wrote files")
                if "fixed" in m.content.lower() or "resolved" in m.content.lower():
                    actions.append("- Fixed issues")

            if actions:
                summary_parts.append(f"Actions taken:\n" + "\n".join(set(actions[:5])))

        if summary_parts:
            return f"[Compressed {len(messages)} messages]\n\n" + "\n\n".join(summary_parts)

        return f"[Compressed {len(messages)} messages - general conversation]"

    def _extract_decisions(self, messages: List[Message]) -> List[str]:
        """Extract key decisions from messages."""
        decisions = []
        decision_keywords = ["decided", "chosen", "will use", "going with", "selected"]

        for m in messages:
            content_lower = m.content.lower()
            for kw in decision_keywords:
                if kw in content_lower:
                    # Extract sentence containing keyword
                    sentences = m.content.split(".")
                    for s in sentences:
                        if kw in s.lower():
                            decisions.append(s.strip()[:200])
                            break

        return decisions[:5]  # Limit to 5 decisions

    def _extract_code_changes(self, messages: List[Message]) -> List[str]:
        """Extract code changes from messages."""
        changes = []

        for m in messages:
            if m.role == "assistant" and "```" in m.content:
                # Look for file paths or descriptions
                lines = m.content.split("\n")
                for i, line in enumerate(lines):
                    if "```" in line and i > 0:
                        prev_line = lines[i - 1].strip()
                        if prev_line:
                            changes.append(prev_line[:100])

        return changes[:5]

    def _extract_topics(self, messages: List[Message]) -> List[str]:
        """Extract main topics discussed."""
        # Simple keyword extraction
        all_content = " ".join([m.content for m in messages])
        words = all_content.lower().split()

        # Count significant words (length > 5, not common)
        common_words = {
            "about",
            "would",
            "could",
            "should",
            "there",
            "their",
            "these",
            "those",
            "which",
            "where",
        }
        word_counts = {}
        for word in words:
            if len(word) > 5 and word.isalpha() and word not in common_words:
                word_counts[word] = word_counts.get(word, 0) + 1

        # Return top topics
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [w for w, c in sorted_words[:5]]

    def get_context_messages(self) -> List[Dict[str, str]]:
        """
        Get messages formatted for the LLM context.
        Includes summaries + recent messages.

        Returns:
            List of message dictionaries with role and content
        """
        context = []

        # Add summaries as system context
        if self.session.summaries:
            summary_text = "\n\n".join(
                [
                    f"[Previous conversation summary - {s.original_count} messages]\n{s.summary}"
                    for s in self.session.summaries
                ]
            )
            context.append(
                {"role": "system", "content": f"# Conversation History\n\n{summary_text}"}
            )

        # Add actual messages
        for msg in self.session.messages:
            context.append({"role": msg.role, "content": msg.content})

        return context

    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent sessions for this project.

        Args:
            limit: Maximum sessions to return

        Returns:
            List of session metadata dictionaries
        """
        sessions = []

        for file in self.sessions_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Filter by project if specified
                if self.project_path and data.get("project_path") != str(self.project_path):
                    continue

                sessions.append(
                    {
                        "session_id": data["session_id"],
                        "created_at": data["created_at"],
                        "updated_at": data["updated_at"],
                        "message_count": len(data.get("messages", [])),
                        "summary_count": len(data.get("summaries", [])),
                        "anchor_count": len(data.get("anchors", [])),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions[:limit]

    def compact(self, target_messages: int = 20):
        """
        Aggressively compact the session.
        Similar to Claude Code's /compact command.

        Args:
            target_messages: Number of messages to keep
        """
        if len(self.session.messages) <= target_messages:
            return

        # Force compression of everything except last target_messages
        to_compress = self.session.messages[:-target_messages]
        to_keep = self.session.messages[-target_messages:]

        # Keep anchors
        anchors_to_preserve = [m for m in to_compress if m.is_anchor]
        non_anchor = [m for m in to_compress if not m.is_anchor]

        if non_anchor:
            summary = self._create_summary(non_anchor)
            self.session.summaries.append(summary)

        self.session.messages = anchors_to_preserve + to_keep
        self.save()

    def clear(self):
        """Clear the current session (keep summaries)."""
        self.session.messages = []
        self.save()

    def delete_session(self, session_id: Optional[str] = None):
        """Delete a session file."""
        sid = session_id or self.session.session_id
        file_path = self._session_file(sid)
        if file_path.exists():
            file_path.unlink()

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            "session_id": self.session.session_id,
            "project_path": self.session.project_path,
            "created_at": self.session.created_at,
            "updated_at": self.session.updated_at,
            "message_count": len(self.session.messages),
            "summary_count": len(self.session.summaries),
            "anchor_count": len(self.session.anchors),
            "compressed_messages": sum(s.original_count for s in self.session.summaries),
            "user_messages": len([m for m in self.session.messages if m.role == "user"]),
            "assistant_messages": len([m for m in self.session.messages if m.role == "assistant"]),
        }

    # Public methods that mirror private ones for external use

    def create_session(self) -> Session:
        """Create a new session (public wrapper)."""
        self.session = self._create_session()
        self.save()
        return self.session

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session by ID (public wrapper)."""
        self.session = self._load_session(session_id)
        return self.session

    def save_session(self):
        """Save the current session (alias for save)."""
        self.save()

    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        """Get existing session or create new one."""
        if session_id:
            return self.load_session(session_id)
        return self.session

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List available sessions (alias for get_recent_sessions)."""
        sessions = []

        for file in self.sessions_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Get last message preview
                messages = data.get("messages", [])
                last_preview = ""
                if messages:
                    last_msg = messages[-1]
                    last_preview = last_msg.get("content", "")[:50]

                sessions.append(
                    {
                        "session_id": data["session_id"],
                        "created_at": data["created_at"],
                        "updated_at": data["updated_at"],
                        "message_count": len(messages),
                        "last_message_preview": last_preview,
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions[:limit]

    def export_session(self, session_id: str, output_path: Path) -> bool:
        """Export a session to a file."""
        file_path = self._session_file(session_id)

        if not file_path.exists():
            return False

        try:
            import shutil

            shutil.copy(file_path, output_path)
            return True
        except Exception:
            return False
