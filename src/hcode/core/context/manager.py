"""
ContextManager for Hcode.
Manages conversation history, context windows, and session persistence.
"""

import json
import os
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from hcode.providers import Message, AIProvider


@dataclass
class ContextEntry:
    """Represents a single entry in the conversation context"""

    role: str
    content: str
    timestamp: str
    tokens: int
    importance: float = 1.0  # 0-1 scale for importance scoring
    tool_calls: Optional[List[Dict]] = None  # Stored as list of dicts
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> "ContextEntry":
        return ContextEntry(**data)


class ContextManager:
    """Manages conversation context and history"""

    def __init__(
        self,
        root_dir: Optional[str] = None,
        session_id: Optional[str] = None,
        fresh_session: bool = True,
    ):
        """
        Initialize ContextManager.

        Args:
            root_dir: Root directory for storing sessions
            session_id: Session identifier (creates new if None)
            fresh_session: If True, start with empty context (default). If False, load previous messages.
        """
        self.root_dir = Path(root_dir or os.getcwd())
        self.session_dir = self.root_dir / ".hcode" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Determine session handling
        if session_id:
            # Use the provided session ID (explicit persistence)
            self.session_id = session_id
        else:
            # No explicit ID – generate a new one
            self.session_id = self._create_session_id()

        self.session_file = self.session_dir / f"{self.session_id}.db"

        self.context: List[ContextEntry] = []
        self.system_prompt: Optional[str] = None

        self._init_database()

        # Load existing session if a session ID was provided (or if the DB already exists)
        if session_id:
            self._load_session()

    def _create_session_id(self) -> str:
        """Create a new session ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _init_database(self):
        """Initialize SQLite database for session storage"""
        conn = sqlite3.connect(self.session_file)
        cursor = conn.cursor()

        # Check if table exists and has new columns
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        table_exists = cursor.fetchone()

        if not table_exists:
            cursor.execute(
                """
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    tokens INTEGER,
                    importance REAL DEFAULT 1.0,
                    tool_calls TEXT,
                    tool_call_id TEXT
                )
            """
            )
        else:
            # Check for missing columns (simple migration)
            cursor.execute("PRAGMA table_info(messages)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if "tool_calls" not in columns:
                try:
                    cursor.execute("ALTER TABLE messages ADD COLUMN tool_calls TEXT")
                except sqlite3.OperationalError:
                    pass # Already exists
            
            if "tool_call_id" not in columns:
                try:
                    cursor.execute("ALTER TABLE messages ADD COLUMN tool_call_id TEXT")
                except sqlite3.OperationalError:
                    pass # Already exists

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        conn.commit()
        conn.close()

    def _load_session(self):
        """Load session from database"""
        conn = sqlite3.connect(self.session_file)
        cursor = conn.cursor()

        # Load messages - check columns first to be safe
        try:
            cursor.execute(
                "SELECT role, content, timestamp, tokens, importance, tool_calls, tool_call_id FROM messages ORDER BY id"
            )
            rows = cursor.fetchall()

            for row in rows:
                tool_calls_data = json.loads(row[5]) if row[5] else None
                self.context.append(
                    ContextEntry(
                        role=row[0], 
                        content=row[1], 
                        timestamp=row[2], 
                        tokens=row[3], 
                        importance=row[4],
                        tool_calls=tool_calls_data,
                        tool_call_id=row[6]
                    )
                )
        except sqlite3.OperationalError:
            # Fallback for old schema if migration failed (shouldn't happen with updated _init)
            cursor.execute(
                "SELECT role, content, timestamp, tokens, importance FROM messages ORDER BY id"
            )
            rows = cursor.fetchall()
            for row in rows:
                self.context.append(
                    ContextEntry(
                        role=row[0], content=row[1], timestamp=row[2], tokens=row[3], importance=row[4]
                    )
                )

        # Load system prompt
        cursor.execute("SELECT value FROM metadata WHERE key = ?", ("system_prompt",))
        result = cursor.fetchone()
        if result:
            self.system_prompt = result[0]

        conn.close()

    def add_message(
        self,
        role: str,
        content: str,
        importance: float = 1.0,
        provider: Optional[AIProvider] = None,
        tool_calls: Optional[List[Dict]] = None,
        tool_call_id: Optional[str] = None,
    ):
        """
        Add a message to the context.

        Args:
            role: Message role (user, assistant, system, tool)
            content: Message content
            importance: Importance score (0-1)
            provider: AI provider for token counting
            tool_calls: List of tool calls (for assistant messages)
            tool_call_id: ID of tool call being responded to (for tool messages)
        """
        # Count tokens
        tokens = provider.count_tokens(content) if provider else len(content) // 4

        entry = ContextEntry(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            tokens=tokens,
            importance=importance,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
        )

        self.context.append(entry)
        self._save_message(entry)

    def _save_message(self, entry: ContextEntry):
        """Save a message to database"""
        conn = sqlite3.connect(self.session_file)
        cursor = conn.cursor()

        tool_calls_json = json.dumps(entry.tool_calls) if entry.tool_calls else None
        
        cursor.execute(
            """
            INSERT INTO messages (role, content, timestamp, tokens, importance, tool_calls, tool_call_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                entry.role, 
                entry.content, 
                entry.timestamp, 
                entry.tokens, 
                entry.importance,
                tool_calls_json,
                entry.tool_call_id
            ),
        )

        conn.commit()
        conn.close()

    def set_system_prompt(self, prompt: str):
        """
        Set the system prompt.

        Args:
            prompt: System prompt text
        """
        self.system_prompt = prompt

        conn = sqlite3.connect(self.session_file)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO metadata (key, value)
            VALUES (?, ?)
        """,
            ("system_prompt", prompt),
        )

        conn.commit()
        conn.close()

    def get_messages(
        self, max_tokens: Optional[int] = None, include_system: bool = True
    ) -> List[Message]:
        """
        Get messages for AI provider.

        Args:
            max_tokens: Maximum tokens to include (uses smart truncation)
            include_system: Include system prompt

        Returns:
            List of messages
        """
        messages = []

        # Add system prompt if requested
        if include_system and self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))

        # Calculate total tokens
        if max_tokens:
            truncated_context = self._smart_truncate(self.context, max_tokens)
        else:
            truncated_context = self.context

        # Convert to Message objects
        from hcode.providers import ToolCall

        for entry in truncated_context:
            # Reconstruct ToolCall objects if present
            tool_calls_objs = None
            if entry.tool_calls:
                tool_calls_objs = []
                for tc in entry.tool_calls:
                    tool_calls_objs.append(ToolCall(
                        id=tc.get("id", ""),
                        name=tc.get("name", ""),
                        arguments=tc.get("arguments", {})
                    ))

            messages.append(Message(
                role=entry.role, 
                content=entry.content,
                tool_calls=tool_calls_objs,
                tool_call_id=entry.tool_call_id
            ))

        return messages

    def _smart_truncate(self, context: List[ContextEntry], max_tokens: int) -> List[ContextEntry]:
        """
        Smart truncation of context based on importance and recency.

        Args:
            context: Full context
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated context
        """
        if not context:
            return []

        # Calculate total tokens
        total_tokens = sum(entry.tokens for entry in context)

        if total_tokens <= max_tokens:
            return context

        # Use importance-based selection
        # Keep most recent messages and highest importance messages

        # Always keep the last few messages (most recent)
        recent_messages = context[-5:]  # Keep last 5 messages
        recent_tokens = sum(entry.tokens for entry in recent_messages)

        remaining_tokens = max_tokens - recent_tokens
        remaining_messages = context[:-5]

        # Sort remaining by importance
        sorted_messages = sorted(
            remaining_messages,
            key=lambda x: x.importance * 0.7 + 0.3,  # Weight importance heavily
            reverse=True,
        )

        # Add messages until we hit token limit
        selected_messages = []
        current_tokens = 0

        for msg in sorted_messages:
            if current_tokens + msg.tokens <= remaining_tokens:
                selected_messages.append(msg)
                current_tokens += msg.tokens
            else:
                break

        # Combine and sort by timestamp to maintain chronological order
        all_messages = selected_messages + recent_messages
        all_messages.sort(key=lambda x: x.timestamp)

        return all_messages

    def convert_for_provider(self, provider_name: str, messages: List[Message]) -> List[Message]:
        """
        Convert message format for specific provider.

        Args:
            provider_name: Target provider (anthropic, openai)
            messages: Messages to convert

        Returns:
            Converted messages
        """
        # Handle provider-specific formatting

        if provider_name.lower() == "anthropic":
            # Anthropic uses separate system parameter
            # Remove system messages from conversation
            return [msg for msg in messages if msg.role != "system"]

        elif provider_name.lower() == "openai":
            # OpenAI includes system messages in conversation
            return messages

        return messages

    def summarize_history(self, provider: AIProvider) -> str:
        """
        Create a summary of the conversation history.

        Args:
            provider: AI provider to use for summarization

        Returns:
            Summary text
        """
        if len(self.context) < 5:
            return "No significant history to summarize."

        # Create a concise summary of actions taken
        user_messages = [e for e in self.context if e.role == "user"]
        assistant_messages = [e for e in self.context if e.role == "assistant"]

        summary = f"Session: {self.session_id}\n"
        summary += f"Messages: {len(self.context)} total ({len(user_messages)} user, {len(assistant_messages)} assistant)\n"
        summary += f"Started: {self.context[0].timestamp if self.context else 'N/A'}\n"

        return summary

    def get_context_stats(self) -> Dict:
        """
        Get statistics about the current context.

        Returns:
            Statistics dictionary
        """
        total_tokens = sum(entry.tokens for entry in self.context)
        avg_importance = (
            sum(entry.importance for entry in self.context) / len(self.context)
            if self.context
            else 0
        )

        role_counts = {}
        for entry in self.context:
            role_counts[entry.role] = role_counts.get(entry.role, 0) + 1

        return {
            "session_id": self.session_id,
            "total_messages": len(self.context),
            "total_tokens": total_tokens,
            "average_importance": avg_importance,
            "role_distribution": role_counts,
            "first_message": self.context[0].timestamp if self.context else None,
            "last_message": self.context[-1].timestamp if self.context else None,
        }

    def clear_context(self, keep_system: bool = True):
        """
        Clear the conversation context.

        Args:
            keep_system: Keep system prompt
        """
        self.context = []

        # Optionally clear database
        conn = sqlite3.connect(self.session_file)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM messages")

        if not keep_system:
            cursor.execute("DELETE FROM metadata WHERE key = ?", ("system_prompt",))
            self.system_prompt = None

        conn.commit()
        conn.close()

    def export_session(self, output_path: str):
        """
        Export session to JSON file.

        Args:
            output_path: Path to export file
        """
        data = {
            "session_id": self.session_id,
            "system_prompt": self.system_prompt,
            "messages": [entry.to_dict() for entry in self.context],
            "stats": self.get_context_stats(),
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    def import_session(self, input_path: str):
        """
        Import session from JSON file.

        Args:
            input_path: Path to import file
        """
        with open(input_path, "r") as f:
            data = json.load(f)

        self.session_id = data.get("session_id", self._create_session_id())
        self.system_prompt = data.get("system_prompt")
        self.context = [ContextEntry.from_dict(entry) for entry in data.get("messages", [])]

        # Save to database
        self.session_file = self.session_dir / f"{self.session_id}.db"
        self._init_database()

        for entry in self.context:
            self._save_message(entry)

        if self.system_prompt:
            self.set_system_prompt(self.system_prompt)

    @staticmethod
    def list_sessions(root_dir: Optional[str] = None) -> List[str]:
        """
        List all available sessions.

        Args:
            root_dir: Root directory to search

        Returns:
            List of session IDs
        """
        session_dir = Path(root_dir or os.getcwd()) / ".hcode" / "sessions"

        if not session_dir.exists():
            return []

        sessions = []
        for db_file in session_dir.glob("*.db"):
            sessions.append(db_file.stem)

        return sorted(sessions, reverse=True)
