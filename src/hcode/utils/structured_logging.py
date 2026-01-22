"""
Structured Logging for HCode.

Provides a consistent logging interface with structured context,
replacing silent exception handling throughout the codebase.
"""

import logging
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from ..config.settings import get_logging_settings


@dataclass
class LogContext:
    """Context for structured log entries."""
    operation: Optional[str] = None
    component: Optional[str] = None
    file_path: Optional[str] = None
    tool_name: Optional[str] = None
    session_id: Optional[str] = None
    additional: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        result = {}
        if self.operation:
            result["operation"] = self.operation
        if self.component:
            result["component"] = self.component
        if self.file_path:
            result["file_path"] = self.file_path
        if self.tool_name:
            result["tool_name"] = self.tool_name
        if self.session_id:
            result["session_id"] = self.session_id
        result.update(self.additional)
        return result


class HCodeLogger:
    """
    Structured logger for HCode with context support.
    
    Provides consistent logging across all components with:
    - Structured context fields
    - Error tracking with stack traces
    - Log level control via settings
    - Both file and console output
    """

    _instances: Dict[str, 'HCodeLogger'] = {}
    _initialized: bool = False

    def __init__(self, name: str = "hcode"):
        """Initialize logger for a component."""
        self.name = name
        self._logger = logging.getLogger(f"hcode.{name}")
        self._context = LogContext()

        # Initialize logging system once
        if not HCodeLogger._initialized:
            self._setup_logging()
            HCodeLogger._initialized = True

    @classmethod
    def get_logger(cls, name: str = "hcode") -> 'HCodeLogger':
        """Get or create a logger instance."""
        if name not in cls._instances:
            cls._instances[name] = cls(name)
        return cls._instances[name]

    def _setup_logging(self) -> None:
        """Set up the logging configuration."""
        try:
            settings = get_logging_settings()
        except Exception:
            # Fallback to defaults if settings not available
            settings = None

        # Get root hcode logger
        root_logger = logging.getLogger("hcode")

        # Clear existing handlers
        root_logger.handlers = []

        # Set level
        level_name = settings.level if settings else "INFO"
        level = getattr(logging, level_name, logging.INFO)
        root_logger.setLevel(level)

        # Console handler with formatting
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_format = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)

        # File handler if enabled
        if settings and settings.file_enabled:
            try:
                log_dir = settings.log_dir
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file = log_dir / f"hcode_{datetime.now().strftime('%Y%m%d')}.log"

                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=settings.max_file_size,
                    backupCount=settings.backup_count,
                    encoding="utf-8"
                )
                file_handler.setLevel(logging.DEBUG)  # File gets all levels
                file_format = logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
                )
                file_handler.setFormatter(file_format)
                root_logger.addHandler(file_handler)
            except Exception:
                # Silently skip file logging if it fails
                pass

    def with_context(self, **kwargs) -> 'HCodeLogger':
        """Create a logger with additional context."""
        new_logger = HCodeLogger.__new__(HCodeLogger)
        new_logger.name = self.name
        new_logger._logger = self._logger
        new_logger._context = LogContext(
            operation=kwargs.get('operation', self._context.operation),
            component=kwargs.get('component', self._context.component),
            file_path=kwargs.get('file_path', self._context.file_path),
            tool_name=kwargs.get('tool_name', self._context.tool_name),
            session_id=kwargs.get('session_id', self._context.session_id),
            additional={**self._context.additional, **kwargs.get('additional', {})}
        )
        return new_logger

    def _format_message(self, message: str, **extra) -> str:
        """Format message with context."""
        context = self._context.to_dict()
        context.update(extra)

        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            return f"{message} [{context_str}]"
        return message

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._logger.debug(self._format_message(message, **kwargs))

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._logger.info(self._format_message(message, **kwargs))

    def warning(self, message: str, error: Optional[str] = None, **kwargs) -> None:
        """Log warning message with optional error details."""
        if error:
            kwargs['error'] = error
        self._logger.warning(self._format_message(message, **kwargs))

    def error(
            self,
            message: str,
            error: Optional[Exception] = None,
            include_traceback: bool = True,
            **kwargs
    ) -> None:
        """
        Log error message with optional exception details.
        
        Args:
            message: Error message
            error: Optional exception object
            include_traceback: Whether to include stack trace
            **kwargs: Additional context
        """
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_msg'] = str(error)

            if include_traceback:
                tb = traceback.format_exc()
                if tb and tb != "NoneType: None\n":
                    kwargs['traceback'] = tb

        self._logger.error(self._format_message(message, **kwargs))

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with full traceback."""
        self._logger.exception(self._format_message(message, **kwargs))


# Import handler for RotatingFileHandler
import logging.handlers

# Module-level convenience functions
_default_logger: Optional[HCodeLogger] = None


def get_logger(name: str = "hcode") -> HCodeLogger:
    """Get a logger instance."""
    return HCodeLogger.get_logger(name)


def log_warning(message: str, error: Optional[str] = None, **kwargs) -> None:
    """Log a warning with the default logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger()
    _default_logger.warning(message, error=error, **kwargs)


def log_error(message: str, error: Optional[Exception] = None, **kwargs) -> None:
    """Log an error with the default logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger()
    _default_logger.error(message, error=error, **kwargs)


def log_debug(message: str, **kwargs) -> None:
    """Log debug message with the default logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger()
    _default_logger.debug(message, **kwargs)


def log_info(message: str, **kwargs) -> None:
    """Log info message with the default logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger()
    _default_logger.info(message, **kwargs)
