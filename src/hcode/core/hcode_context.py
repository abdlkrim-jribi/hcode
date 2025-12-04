"""
Hcode Context Manager.
Manages conversation context, session state, and memory.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque
import pickle
import uuid


@dataclass
class Message:
    """Represents a message in the conversation"""

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ConversationContext:
    """Maintains conversation context"""

    messages: List[Message] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    todos: List[Dict[str, str]] = field(default_factory=list)
    workspace_info: Dict[str, Any] = field(default_factory=dict)
    active_tools: List[str] = field(default_factory=list)
    cost_tracking: Dict[str, float] = field(default_factory=dict)


class HcodeContextManager:
    """
    Manage conversation context for Hcode.

    Features:
    - Context window management
    - Session persistence
    - Memory optimization
    - Context summarization
    - Tool usage tracking
    """

    def __init__(
        self,
        max_context_length: int = 100000,
        session_dir: Optional[Path] = None,
        auto_save: bool = True,
    ):
        """
        Initialize context manager.

        Args:
            max_context_length: Maximum context length in tokens
            session_dir: Directory for session persistence
            auto_save: Automatically save sessions
        """
        self.max_context_length = max_context_length
        self.session_dir = Path(session_dir or ".hcode_sessions")
        self.auto_save = auto_save
        self.current_context = ConversationContext()
        self.context_cache = {}

        # Create session directory
        if self.auto_save:
            self.session_dir.mkdir(exist_ok=True)

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        """Add a message to the context"""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
            tool_calls=tool_calls or [],
            tool_results=tool_results or [],
        )

        self.current_context.messages.append(message)
        self.current_context.updated_at = datetime.now()

        # Auto-save if enabled
        if self.auto_save:
            self.save_session()

        # Manage context window
        self._manage_context_window()

        return message

    def _manage_context_window(self):
        """Manage context window size"""
        # Estimate token count (simplified)
        total_tokens = sum(
            len(msg.content.split()) * 1.3  # Rough token estimate
            for msg in self.current_context.messages
        )

        # If exceeding limit, summarize older messages
        if total_tokens > self.max_context_length:
            self._compress_context()

    def _compress_context(self):
        """Compress older context to fit window"""
        # Keep system message and recent messages
        if not self.current_context.messages:
            return

        # Find system message
        system_msg = None
        other_msgs = []

        for msg in self.current_context.messages:
            if msg.role == "system":
                system_msg = msg
            else:
                other_msgs.append(msg)

        # Keep last N messages that fit
        keep_messages = []
        token_count = 0
        max_keep = self.max_context_length * 0.8  # Keep 80% for recent

        for msg in reversed(other_msgs):
            msg_tokens = len(msg.content.split()) * 1.3
            if token_count + msg_tokens < max_keep:
                keep_messages.insert(0, msg)
                token_count += msg_tokens
            else:
                break

        # Create summary of older messages
        older_messages = other_msgs[: len(other_msgs) - len(keep_messages)]
        if older_messages:
            summary = self._create_summary(older_messages)
            summary_msg = Message(
                role="system",
                content=f"Previous conversation summary: {summary}",
                metadata={"type": "summary", "messages_summarized": len(older_messages)},
            )
            keep_messages.insert(0, summary_msg)

        # Rebuild messages list
        self.current_context.messages = []
        if system_msg:
            self.current_context.messages.append(system_msg)
        self.current_context.messages.extend(keep_messages)

    def _create_summary(self, messages: List[Message]) -> str:
        """Create summary of messages"""
        # In production, this would use AI to create intelligent summaries
        # For now, create a simple summary
        summary_parts = []

        # Count message types
        user_count = sum(1 for m in messages if m.role == "user")
        assistant_count = sum(1 for m in messages if m.role == "assistant")

        summary_parts.append(
            f"Previous {len(messages)} messages ({user_count} user, {assistant_count} assistant)"
        )

        # Extract key topics (simplified)
        all_content = " ".join(m.content[:100] for m in messages[-5:])
        summary_parts.append(f"Recent topics: {all_content[:200]}...")

        # Tool usage
        tools_used = set()
        for msg in messages:
            for tool_call in msg.tool_calls:
                tools_used.add(tool_call.get("tool", "unknown"))

        if tools_used:
            summary_parts.append(f"Tools used: {', '.join(tools_used)}")

        return " | ".join(summary_parts)

    def get_context_for_completion(
        self, max_messages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get context formatted for AI completion"""
        messages = self.current_context.messages

        if max_messages:
            messages = messages[-max_messages:]

        formatted = []
        for msg in messages:
            formatted_msg = {"role": msg.role, "content": msg.content}

            # Add tool calls if present
            if msg.tool_calls:
                formatted_msg["tool_calls"] = msg.tool_calls

            # Add tool results if present
            if msg.tool_results:
                formatted_msg["tool_results"] = msg.tool_results

            formatted.append(formatted_msg)

        return formatted

    def update_todos(self, todos: List[Dict[str, str]]):
        """Update todo list in context"""
        self.current_context.todos = todos
        self.current_context.updated_at = datetime.now()

        if self.auto_save:
            self.save_session()

    def update_workspace_info(self, info: Dict[str, Any]):
        """Update workspace information"""
        self.current_context.workspace_info.update(info)
        self.current_context.updated_at = datetime.now()

        if self.auto_save:
            self.save_session()

    def track_tool_usage(self, tool_name: str):
        """Track tool usage"""
        if tool_name not in self.current_context.active_tools:
            self.current_context.active_tools.append(tool_name)

    def track_cost(self, provider: str, cost: float):
        """Track API costs"""
        if provider not in self.current_context.cost_tracking:
            self.current_context.cost_tracking[provider] = 0
        self.current_context.cost_tracking[provider] += cost

    def save_session(self, session_id: Optional[str] = None):
        """Save session to disk"""
        session_id = session_id or self.current_context.session_id
        session_file = self.session_dir / f"{session_id}.json"

        # Convert to serializable format
        data = {
            "session_id": self.current_context.session_id,
            "created_at": self.current_context.created_at.isoformat(),
            "updated_at": self.current_context.updated_at.isoformat(),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata,
                    "tool_calls": msg.tool_calls,
                    "tool_results": msg.tool_results,
                }
                for msg in self.current_context.messages
            ],
            "todos": self.current_context.todos,
            "workspace_info": self.current_context.workspace_info,
            "active_tools": self.current_context.active_tools,
            "cost_tracking": self.current_context.cost_tracking,
            "metadata": self.current_context.metadata,
        }

        with open(session_file, "w") as f:
            json.dump(data, f, indent=2)

    def load_session(self, session_id: str) -> bool:
        """Load session from disk"""
        session_file = self.session_dir / f"{session_id}.json"

        if not session_file.exists():
            return False

        with open(session_file, "r") as f:
            data = json.load(f)

        # Restore context
        self.current_context = ConversationContext(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=[
                Message(
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=datetime.fromisoformat(msg["timestamp"]),
                    metadata=msg["metadata"],
                    tool_calls=msg["tool_calls"],
                    tool_results=msg["tool_results"],
                )
                for msg in data["messages"]
            ],
            todos=data.get("todos", []),
            workspace_info=data.get("workspace_info", {}),
            active_tools=data.get("active_tools", []),
            cost_tracking=data.get("cost_tracking", {}),
            metadata=data.get("metadata", {}),
        )

        return True

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List available sessions"""
        sessions = []

        for session_file in self.session_dir.glob("*.json"):
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                    sessions.append(
                        {
                            "session_id": data["session_id"],
                            "created_at": data["created_at"],
                            "updated_at": data["updated_at"],
                            "message_count": len(data.get("messages", [])),
                            "todo_count": len(data.get("todos", [])),
                        }
                    )
            except:
                continue

        return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)

    def clear_context(self, keep_system: bool = True):
        """Clear conversation context"""
        system_msg = None

        if keep_system and self.current_context.messages:
            for msg in self.current_context.messages:
                if msg.role == "system":
                    system_msg = msg
                    break

        # Create new context
        self.current_context = ConversationContext(session_id=str(uuid.uuid4()))

        if system_msg:
            self.current_context.messages.append(system_msg)

    def export_conversation(self, format: str = "markdown") -> str:
        """Export conversation in specified format"""
        if format == "markdown":
            return self._export_markdown()
        elif format == "json":
            return self._export_json()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_markdown(self) -> str:
        """Export as markdown"""
        lines = []
        lines.append(f"# Conversation {self.current_context.session_id}")
        lines.append(f"*Created: {self.current_context.created_at}*")
        lines.append("")

        for msg in self.current_context.messages:
            role_header = "👤 User" if msg.role == "user" else "🤖 Assistant"
            lines.append(f"## {role_header}")
            lines.append(f"*{msg.timestamp}*")
            lines.append("")
            lines.append(msg.content)
            lines.append("")

            if msg.tool_calls:
                lines.append("### Tools Called:")
                for tool in msg.tool_calls:
                    lines.append(f"- {tool.get('tool', 'unknown')}")
                lines.append("")

        if self.current_context.todos:
            lines.append("## Todo List")
            for todo in self.current_context.todos:
                status = "✅" if todo.get("status") == "completed" else "⏳"
                lines.append(f"- {status} {todo.get('content', '')}")
            lines.append("")

        return "\n".join(lines)

    def _export_json(self) -> str:
        """Export as JSON"""
        data = {
            "session_id": self.current_context.session_id,
            "created_at": self.current_context.created_at.isoformat(),
            "updated_at": self.current_context.updated_at.isoformat(),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata,
                    "tool_calls": msg.tool_calls,
                    "tool_results": msg.tool_results,
                }
                for msg in self.current_context.messages
            ],
            "todos": self.current_context.todos,
            "workspace_info": self.current_context.workspace_info,
            "cost_tracking": self.current_context.cost_tracking,
        }
        return json.dumps(data, indent=2)

    def get_statistics(self) -> Dict[str, Any]:
        """Get context statistics"""
        return {
            "session_id": self.current_context.session_id,
            "message_count": len(self.current_context.messages),
            "user_messages": sum(1 for m in self.current_context.messages if m.role == "user"),
            "assistant_messages": sum(
                1 for m in self.current_context.messages if m.role == "assistant"
            ),
            "todo_count": len(self.current_context.todos),
            "completed_todos": sum(
                1 for t in self.current_context.todos if t.get("status") == "completed"
            ),
            "tools_used": len(self.current_context.active_tools),
            "total_cost": sum(self.current_context.cost_tracking.values()),
            "cost_by_provider": self.current_context.cost_tracking,
            "session_duration": (datetime.now() - self.current_context.created_at).total_seconds()
            / 60,  # in minutes
        }
