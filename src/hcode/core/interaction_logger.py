"""
Interaction Logger for HCODE Agent.

Logs all model interactions, tool calls, and their complete outputs
for debugging and enhancement purposes.

Features:
- Session-based logging with timestamps
- Full output capture (no truncation)
- Structured JSON format for easy parsing
- Rolling log files with size limits
- Query interface for analysis
"""

import gzip
import json
import shutil
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass
class ToolCallLog:
    """Log entry for a tool call"""

    timestamp: str
    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    output: str  # Full output - not truncated
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelInteractionLog:
    """Log entry for a model interaction"""

    timestamp: str
    iteration: int
    request_messages: List[Dict[str, Any]]
    response_text: str  # Full response - not truncated
    finish_reason: str
    tool_calls_detected: int
    tool_calls: List[ToolCallLog] = field(default_factory=list)
    continuation_needed: bool = False
    pending_work_detected: bool = False
    tokens_used: Dict[str, int] = field(default_factory=dict)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionLog:
    """Complete session log"""

    session_id: str
    start_time: str
    end_time: Optional[str] = None
    initial_task: str = ""
    provider: str = ""
    model: str = ""
    total_iterations: int = 0
    total_tool_calls: int = 0
    interactions: List[ModelInteractionLog] = field(default_factory=list)
    final_result: str = ""
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class InteractionLogger:
    """
    Comprehensive logger for model interactions.

    Usage:
        logger = InteractionLogger()
        logger.start_session(task="run tests", provider="openai", model="gpt-oss-120b")

        # Log each iteration
        logger.log_interaction(
            iteration=1,
            request_messages=[...],
            response_text="...",
            finish_reason="stop",
            tool_calls=[...]
        )

        # End session
        logger.end_session(final_result="...", errors=[])
    """

    # Class-level singleton pattern for global access
    _instance: Optional["InteractionLogger"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        log_dir: Optional[str] = None,
        max_file_size_mb: int = 50,
        max_files: int = 10,
        compress_old: bool = True,
    ):
        """
        Initialize the interaction logger.

        Args:
            log_dir: Directory to store logs (default: ~/.hcode/logs)
            max_file_size_mb: Max size of each log file in MB
            max_files: Max number of log files to keep
            compress_old: Whether to compress old log files
        """
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path.home() / ".hcode" / "logs"

        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.max_files = max_files
        self.compress_old = compress_old

        self.current_session: Optional[SessionLog] = None
        self.current_log_file: Optional[Path] = None
        self._file_lock = threading.Lock()

    @classmethod
    def get_instance(cls, **kwargs) -> "InteractionLogger":
        """Get or create the singleton logger instance"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(**kwargs)
            return cls._instance

    def start_session(
        self,
        task: str,
        provider: str = "",
        model: str = "",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start a new logging session.

        Args:
            task: Initial task description
            provider: Provider name (openai, anthropic, etc.)
            model: Model name
            session_id: Optional custom session ID
            metadata: Optional metadata dict

        Returns:
            Session ID
        """
        import uuid

        sid = (
            session_id
            or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )

        self.current_session = SessionLog(
            session_id=sid,
            start_time=datetime.now().isoformat(),
            initial_task=task,
            provider=provider,
            model=model,
            metadata=metadata or {},
        )

        # Create log file for this session
        self.current_log_file = self.log_dir / f"{sid}.jsonl"

        # Write session header
        self._write_log_entry(
            {
                "type": "session_start",
                "session_id": sid,
                "start_time": self.current_session.start_time,
                "task": task,
                "provider": provider,
                "model": model,
                "metadata": metadata or {},
            }
        )

        return sid

    def log_interaction(
        self,
        iteration: int,
        request_messages: List[Dict[str, Any]],
        response_text: str,
        finish_reason: str,
        tool_calls_detected: int = 0,
        continuation_needed: bool = False,
        pending_work_detected: bool = False,
        tokens_used: Optional[Dict[str, int]] = None,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModelInteractionLog:
        """
        Log a model interaction.

        Args:
            iteration: Iteration number
            request_messages: Messages sent to model
            response_text: Full response text (not truncated!)
            finish_reason: API finish reason
            tool_calls_detected: Number of tool calls detected
            continuation_needed: Whether continuation was triggered
            pending_work_detected: Whether pending work was detected
            tokens_used: Token usage stats
            duration_ms: Duration in milliseconds
            metadata: Additional metadata

        Returns:
            The log entry
        """
        if not self.current_session:
            self.start_session(task="(no task)", provider="unknown")

        log = ModelInteractionLog(
            timestamp=datetime.now().isoformat(),
            iteration=iteration,
            request_messages=request_messages,
            response_text=response_text,
            finish_reason=finish_reason,
            tool_calls_detected=tool_calls_detected,
            continuation_needed=continuation_needed,
            pending_work_detected=pending_work_detected,
            tokens_used=tokens_used or {},
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        self.current_session.interactions.append(log)
        self.current_session.total_iterations = iteration

        # Write to file
        self._write_log_entry({"type": "interaction", **asdict(log)})

        return log

    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        success: bool,
        output: str,
        error: Optional[str] = None,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolCallLog:
        """
        Log a tool call with full output.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            success: Whether the tool succeeded
            output: Full tool output (not truncated!)
            error: Error message if failed
            duration_ms: Duration in milliseconds
            metadata: Additional metadata

        Returns:
            The log entry
        """
        if not self.current_session:
            self.start_session(task="(no task)", provider="unknown")

        log = ToolCallLog(
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            arguments=arguments,
            success=success,
            output=output,
            error=error,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        # Add to current interaction if there is one
        if self.current_session.interactions:
            self.current_session.interactions[-1].tool_calls.append(log)

        self.current_session.total_tool_calls += 1

        # Write to file
        self._write_log_entry({"type": "tool_call", **asdict(log)})

        return log

    def log_error(self, error: str, context: Optional[Dict[str, Any]] = None):
        """Log an error"""
        if not self.current_session:
            self.start_session(task="(no task)", provider="unknown")

        self.current_session.errors.append(error)

        self._write_log_entry(
            {
                "type": "error",
                "timestamp": datetime.now().isoformat(),
                "error": error,
                "context": context or {},
            }
        )

    def log_continuation_prompt(self, prompt: str, reason: str):
        """Log a continuation prompt sent to the model"""
        self._write_log_entry(
            {
                "type": "continuation_prompt",
                "timestamp": datetime.now().isoformat(),
                "prompt": prompt,
                "reason": reason,
            }
        )

    def end_session(
        self,
        final_result: str = "",
        errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        End the current logging session.

        Args:
            final_result: Final result of the task
            errors: List of errors encountered
            metadata: Additional metadata
        """
        if not self.current_session:
            return

        self.current_session.end_time = datetime.now().isoformat()
        self.current_session.final_result = final_result
        if errors:
            self.current_session.errors.extend(errors)
        if metadata:
            self.current_session.metadata.update(metadata)

        # Write session footer
        self._write_log_entry(
            {
                "type": "session_end",
                "session_id": self.current_session.session_id,
                "end_time": self.current_session.end_time,
                "total_iterations": self.current_session.total_iterations,
                "total_tool_calls": self.current_session.total_tool_calls,
                "final_result_length": len(final_result),
                "error_count": len(self.current_session.errors),
                "metadata": metadata or {},
            }
        )

        # Rotate logs if needed
        self._rotate_logs()

        self.current_session = None
        self.current_log_file = None

    def _write_log_entry(self, entry: Dict[str, Any]):
        """Write a log entry to file"""
        if not self.current_log_file:
            return

        with self._file_lock:
            try:
                with open(self.current_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            except Exception as e:
                print(f"Warning: Failed to write log entry: {e}")

    def _rotate_logs(self):
        """Rotate and compress old log files if needed"""
        if not self.current_log_file or not self.current_log_file.exists():
            return

        # Check file size
        if self.current_log_file.stat().st_size > self.max_file_size:
            # Compress current file
            if self.compress_old:
                compressed = self.current_log_file.with_suffix(".jsonl.gz")
                with open(self.current_log_file, "rb") as f_in:
                    with gzip.open(compressed, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                self.current_log_file.unlink()

        # Cleanup old files
        log_files = sorted(
            self.log_dir.glob("session_*.jsonl*"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        if len(log_files) > self.max_files:
            for old_file in log_files[self.max_files :]:
                old_file.unlink()

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session"""
        if not self.current_session:
            return {"active": False}

        return {
            "active": True,
            "session_id": self.current_session.session_id,
            "start_time": self.current_session.start_time,
            "task": self.current_session.initial_task,
            "provider": self.current_session.provider,
            "model": self.current_session.model,
            "iterations": self.current_session.total_iterations,
            "tool_calls": self.current_session.total_tool_calls,
            "errors": len(self.current_session.errors),
            "log_file": str(self.current_log_file) if self.current_log_file else None,
        }

    def get_recent_logs(self, count: int = 100) -> List[Dict[str, Any]]:
        """Get recent log entries from current session"""
        if not self.current_log_file or not self.current_log_file.exists():
            return []

        entries = []
        try:
            with open(self.current_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception:
            pass

        return entries[-count:]

    def query_logs(
        self,
        log_type: Optional[str] = None,
        tool_name: Optional[str] = None,
        success_only: bool = False,
        failed_only: bool = False,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query logs with filters.

        Args:
            log_type: Filter by type (interaction, tool_call, error, etc.)
            tool_name: Filter by tool name
            success_only: Only include successful operations
            failed_only: Only include failed operations
            since: Only include entries after this time

        Returns:
            List of matching log entries
        """
        results = []

        for log_file in sorted(self.log_dir.glob("session_*.jsonl")):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        entry = json.loads(line)

                        # Apply filters
                        if log_type and entry.get("type") != log_type:
                            continue
                        if tool_name and entry.get("tool_name") != tool_name:
                            continue
                        if success_only and not entry.get("success", True):
                            continue
                        if failed_only and entry.get("success", False):
                            continue
                        if since:
                            entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                            if entry_time < since:
                                continue

                        results.append(entry)
            except Exception:
                continue

        return results

    def get_failed_tool_calls(self) -> List[Dict[str, Any]]:
        """Get all failed tool calls for analysis"""
        return self.query_logs(log_type="tool_call", failed_only=True)

    def get_truncated_outputs(self, min_length: int = 1000) -> List[Dict[str, Any]]:
        """
        Find log entries where output might have been truncated.

        Note: This checks the logged output, which should be complete.
        It helps identify where the display was truncated but full output exists.
        """
        results = []

        for entry in self.query_logs(log_type="tool_call"):
            output = entry.get("output", "")
            if len(output) > min_length:
                results.append(
                    {
                        "tool_name": entry.get("tool_name"),
                        "output_length": len(output),
                        "timestamp": entry.get("timestamp"),
                        "preview": output[:200] + "..." if len(output) > 200 else output,
                    }
                )

        return results

    def export_session_report(self, session_id: str, output_path: str) -> bool:
        """
        Export a complete session report as markdown.

        Args:
            session_id: Session ID to export
            output_path: Path for output file

        Returns:
            True if successful
        """
        log_file = self.log_dir / f"{session_id}.jsonl"
        if not log_file.exists():
            return False

        entries = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

        # Build markdown report
        report = [f"# Session Report: {session_id}\n"]

        # Session info
        for entry in entries:
            if entry.get("type") == "session_start":
                report.append(f"**Task:** {entry.get('task')}\n")
                report.append(f"**Provider:** {entry.get('provider')}\n")
                report.append(f"**Model:** {entry.get('model')}\n")
                report.append(f"**Start Time:** {entry.get('start_time')}\n")
                break

        report.append("\n## Interactions\n")

        interaction_num = 0
        for entry in entries:
            if entry.get("type") == "interaction":
                interaction_num += 1
                report.append(f"\n### Iteration {entry.get('iteration')}\n")
                report.append(f"- **Finish Reason:** {entry.get('finish_reason')}\n")
                report.append(f"- **Tool Calls:** {entry.get('tool_calls_detected')}\n")
                report.append(f"- **Continuation Needed:** {entry.get('continuation_needed')}\n")
                report.append(
                    f"\n**Response:**\n```\n{entry.get('response_text', '')[:500]}...\n```\n"
                )

            elif entry.get("type") == "tool_call":
                report.append(f"\n#### Tool: {entry.get('tool_name')}\n")
                report.append(f"- **Success:** {entry.get('success')}\n")
                if entry.get("error"):
                    report.append(f"- **Error:** {entry.get('error')}\n")
                report.append(
                    f"\n**Arguments:**\n```json\n{json.dumps(entry.get('arguments', {}), indent=2)}\n```\n"
                )
                output = entry.get("output", "")
                if output:
                    report.append(
                        f"\n**Output ({len(output)} chars):**\n```\n{output[:1000]}{'...' if len(output) > 1000 else ''}\n```\n"
                    )

            elif entry.get("type") == "error":
                report.append(f"\n### ⚠️ Error\n```\n{entry.get('error')}\n```\n")

        # Summary
        for entry in entries:
            if entry.get("type") == "session_end":
                report.append(f"\n## Summary\n")
                report.append(f"- **Total Iterations:** {entry.get('total_iterations')}\n")
                report.append(f"- **Total Tool Calls:** {entry.get('total_tool_calls')}\n")
                report.append(f"- **Errors:** {entry.get('error_count')}\n")
                report.append(f"- **End Time:** {entry.get('end_time')}\n")
                break

        # Write report
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report))

        return True


# Global logger instance access
def get_logger(**kwargs) -> InteractionLogger:
    """Get the global interaction logger instance"""
    return InteractionLogger.get_instance(**kwargs)


def start_logging(task: str, provider: str = "", model: str = "", **kwargs) -> str:
    """Start a new logging session"""
    return get_logger().start_session(task=task, provider=provider, model=model, **kwargs)


def log_interaction(**kwargs) -> ModelInteractionLog:
    """Log a model interaction"""
    return get_logger().log_interaction(**kwargs)


def log_tool_call(**kwargs) -> ToolCallLog:
    """Log a tool call"""
    return get_logger().log_tool_call(**kwargs)


def log_error(error: str, context: Optional[Dict[str, Any]] = None):
    """Log an error"""
    get_logger().log_error(error, context)


def end_logging(**kwargs):
    """End the current logging session"""
    get_logger().end_session(**kwargs)
