"""
Configuration for the HCODE agent memory system.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MemoryConfig:
    """
    Configuration for the three-layer memory system.

    Attributes:
        global_dir: Base directory for global agent data (~/.hcode)
        global_memory_file: Name of global memory file (AGENT.md)
        project_memory_file: Name of project memory file (AGENT.md)
        local_memory_file: Name of local memory file (AGENT.local.md) - gitignored
        sessions_dir: Directory for session storage
        max_recent_messages: Number of recent messages to keep uncompressed
        compression_threshold: Trigger compression when exceeding this count
        db_file: SQLite database file for semantic memory
        embedding_model: Local embedding model name
        embedding_dim: Dimension of embeddings
        max_retrieval_results: Max results for semantic search
    """

    # Base directories
    global_dir: Path = field(default_factory=lambda: Path.home() / ".hcode")

    # File memory settings
    global_memory_file: str = "AGENT.md"
    project_memory_file: str = "AGENT.md"
    local_memory_file: str = "AGENT.local.md"  # gitignored

    # Session settings
    sessions_dir: str = "sessions"
    max_recent_messages: int = 50  # Keep full history for last N messages
    compression_threshold: int = 100  # Compress when exceeding this
    anchor_keywords: tuple = field(
        default_factory=lambda: (
            "always",
            "never",
            "critical",
            "key decision",
            "architecture",
            "design choice",
        )
    )

    # Semantic memory settings
    db_file: str = "memory.db"
    embedding_model: str = "all-MiniLM-L6-v2"  # Local model
    embedding_dim: int = 384
    max_retrieval_results: int = 10

    # Pruning settings
    max_memories: int = 10000
    max_context_tokens: int = 4096

    def __post_init__(self):
        """Ensure directories exist."""
        self.global_dir = Path(self.global_dir)
        self.global_dir.mkdir(parents=True, exist_ok=True)
        (self.global_dir / self.sessions_dir).mkdir(exist_ok=True)

    @property
    def sessions_path(self) -> Path:
        """Get full path to sessions directory."""
        return self.global_dir / self.sessions_dir

    @property
    def db_path(self) -> Path:
        """Get full path to database file."""
        return self.global_dir / self.db_file

    @property
    def global_memory_path(self) -> Path:
        """Get full path to global memory file."""
        return self.global_dir / self.global_memory_file

    def get_project_memory_path(self, project_root: Path) -> Path:
        """Get path to project memory file."""
        return project_root / self.project_memory_file

    def get_local_memory_path(self, project_root: Path) -> Path:
        """Get path to local memory file."""
        return project_root / self.local_memory_file


# Singleton config instance
config = MemoryConfig()


def get_config() -> MemoryConfig:
    """Get the global config instance."""
    return config


def update_config(**kwargs) -> MemoryConfig:
    """Update config with new values."""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config
