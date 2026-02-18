"""
Tests for the HCODE Infinite Memory System.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestMemoryConfig:
    """Test MemoryConfig class."""

    def test_config_defaults(self):
        """Test default configuration values."""
        from src.hcode.memory.config import MemoryConfig

        config = MemoryConfig()

        assert config.global_memory_file == "AGENT.md"
        assert config.project_memory_file == "AGENT.md"
        assert config.local_memory_file == "AGENT.local.md"
        assert config.max_recent_messages == 50
        assert config.compression_threshold == 100
        assert config.embedding_model == "all-MiniLM-L6-v2"
        assert config.embedding_dim == 384

    def test_config_paths(self):
        """Test path properties."""
        from src.hcode.memory.config import MemoryConfig

        config = MemoryConfig()

        assert config.global_memory_path.name == "AGENT.md"
        assert "sessions" in str(config.sessions_path)


class TestFileMemory:
    """Test FileMemory class (Layer 1)."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        # Create a .git marker to simulate a project root
        (Path(temp_dir) / ".git").mkdir()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_detect_project_root(self, temp_project):
        """Test project root detection."""
        from src.hcode.memory.file_memory import FileMemory

        # Create FileMemory from within the project
        import os

        original_cwd = os.getcwd()
        os.chdir(temp_project)
        try:
            fm = FileMemory()
            assert fm.project_root == temp_project
        finally:
            os.chdir(original_cwd)

    def test_create_template(self, temp_project):
        """Test template generation."""
        from src.hcode.memory.file_memory import FileMemory

        fm = FileMemory(temp_project)

        # Test project template
        template = fm.create_template("project")
        assert "# Project HCODE Agent Memory" in template
        assert "## Tech Stack" in template
        assert "## Architecture" in template

        # Test global template
        global_template = fm.create_template("global")
        assert "# Global HCODE Agent Memory" in global_template
        assert "## User Preferences" in global_template

    def test_update_memory(self, temp_project):
        """Test updating memory files."""
        from src.hcode.memory.file_memory import FileMemory

        fm = FileMemory(temp_project)

        # Write project memory
        content = "# Test Memory\n\nThis is a test."
        path = fm.update_memory(content, scope="project")

        assert path.exists()
        assert path.read_text() == content

    def test_get_memory_files(self, temp_project):
        """Test retrieving memory files."""
        from src.hcode.memory.file_memory import FileMemory

        fm = FileMemory(temp_project)

        # Create project memory
        fm.update_memory("# Project Memory", scope="project")

        files = fm.get_memory_files()
        assert len(files) >= 1
        assert any(f.scope == "project" for f in files)

    def test_combined_context(self, temp_project):
        """Test getting combined context."""
        from src.hcode.memory.file_memory import FileMemory

        fm = FileMemory(temp_project)

        # Create memories
        fm.update_memory("# Project\nProject info", scope="project")
        fm.update_memory("# Local\nLocal info", scope="local")

        context = fm.get_combined_context()
        assert "Project Memory" in context or "Project info" in context


class TestSessionMemory:
    """Test SessionMemory class (Layer 2)."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        (Path(temp_dir) / ".git").mkdir()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_create_session(self, temp_project):
        """Test creating a new session."""
        from src.hcode.memory.session_memory import SessionMemory

        sm = SessionMemory(temp_project)
        session = sm.create_session()

        assert session is not None
        assert session.session_id is not None
        assert session.created_at is not None

    def test_add_message(self, temp_project):
        """Test adding messages to session."""
        from src.hcode.memory.session_memory import SessionMemory

        sm = SessionMemory(temp_project)
        sm.create_session()

        msg = sm.add_message("user", "Hello, agent!")
        assert msg.role == "user"
        assert msg.content == "Hello, agent!"
        assert not msg.is_anchor

    def test_anchor_messages(self, temp_project):
        """Test anchor message detection."""
        from src.hcode.memory.session_memory import SessionMemory

        sm = SessionMemory(temp_project)
        sm.create_session()

        # Add a message with anchor keyword
        msg = sm.add_message("user", "IMPORTANT: Always use type hints", auto_anchor=True)
        assert msg.is_anchor

    def test_session_persistence(self, temp_project):
        """Test session save and load."""
        from src.hcode.memory.session_memory import SessionMemory

        sm = SessionMemory(temp_project)
        session = sm.create_session()
        session_id = session.session_id

        sm.add_message("user", "Test message")
        sm.save_session()

        # Create new SessionMemory and load
        sm2 = SessionMemory(temp_project)
        loaded = sm2.load_session(session_id)

        assert loaded is not None
        assert loaded.session_id == session_id
        assert len(loaded.messages) == 1

    def test_context_messages(self, temp_project):
        """Test getting context messages."""
        from src.hcode.memory.session_memory import SessionMemory

        sm = SessionMemory(temp_project)
        sm.create_session()

        sm.add_message("user", "Hello")
        sm.add_message("assistant", "Hi there!")

        messages = sm.get_context_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"


class TestEmbeddings:
    """Test embedding system."""

    def test_fallback_embedding(self):
        """Test fallback embedding when sentence-transformers not available."""
        from src.hcode.memory.embeddings import FallbackEmbedding
        import numpy as np

        fb = FallbackEmbedding(dim=384)
        embedding = fb.embed("Hello world")

        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384

    def test_fallback_batch_embed(self):
        """Test batch embedding with fallback."""
        from src.hcode.memory.embeddings import FallbackEmbedding
        import numpy as np

        fb = FallbackEmbedding(dim=384)
        embeddings = fb.embed_batch(["Hello", "World", "Test"])

        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 384)

    def test_embedding_model_safe(self):
        """Test safe embedding model retrieval."""
        from src.hcode.memory.embeddings import get_embedding_model_safe

        model = get_embedding_model_safe()
        assert model is not None

        # Should work regardless of sentence-transformers availability
        embedding = model.embed("Test text")
        assert len(embedding) > 0


class TestSemanticMemory:
    """Test SemanticMemory class (Layer 3)."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_memory.db"
        yield db_path
        shutil.rmtree(temp_dir)

    def test_add_memory(self, temp_db):
        """Test adding memories."""
        from src.hcode.memory.semantic_memory import SemanticMemory, MemoryType

        sm = SemanticMemory(db_path=temp_db)
        memory = sm.add(
            content="Python uses snake_case for variable names",
            memory_type=MemoryType.FACT,
            importance=0.8,
        )

        assert memory.id is not None
        assert memory.content == "Python uses snake_case for variable names"
        assert memory.memory_type == MemoryType.FACT

    def test_search_memories(self, temp_db):
        """Test searching memories."""
        from src.hcode.memory.semantic_memory import SemanticMemory, MemoryType

        sm = SemanticMemory(db_path=temp_db)

        # Add some memories
        sm.add("Python is a programming language", MemoryType.FACT, importance=0.8)
        sm.add("JavaScript runs in browsers", MemoryType.FACT, importance=0.7)
        sm.add("Use camelCase in JavaScript", MemoryType.CODE_PATTERN, importance=0.6)

        # Search
        results = sm.search("Python programming", top_k=2)

        assert len(results) > 0
        # First result should be about Python
        assert "python" in results[0][0].content.lower()

    def test_memory_type_filter(self, temp_db):
        """Test filtering by memory type."""
        from src.hcode.memory.semantic_memory import SemanticMemory, MemoryType

        sm = SemanticMemory(db_path=temp_db)

        sm.add("Fact 1", MemoryType.FACT)
        sm.add("Preference 1", MemoryType.PREFERENCE)

        # Search with type filter
        results = sm.search("", memory_types=[MemoryType.PREFERENCE])

        assert all(m[0].memory_type == MemoryType.PREFERENCE for m in results)

    def test_prune_memories(self, temp_db):
        """Test pruning low-importance memories."""
        from src.hcode.memory.semantic_memory import SemanticMemory, MemoryType

        sm = SemanticMemory(db_path=temp_db)

        # Add memories with different importance
        sm.add("Low importance", MemoryType.CONTEXT, importance=0.1)
        sm.add("High importance", MemoryType.CONTEXT, importance=0.9)

        deleted = sm.prune(min_importance=0.5)

        assert deleted == 1  # Low importance should be deleted

    def test_get_stats(self, temp_db):
        """Test memory statistics."""
        from src.hcode.memory.semantic_memory import SemanticMemory, MemoryType

        sm = SemanticMemory(db_path=temp_db)

        sm.add("Memory 1", MemoryType.FACT)
        sm.add("Memory 2", MemoryType.PREFERENCE)

        stats = sm.get_stats()

        assert stats["total_memories"] == 2
        assert "fact" in stats["by_type"]


class TestMemoryManager:
    """Test unified MemoryManager."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        (Path(temp_dir) / ".git").mkdir()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_init_manager(self, temp_project):
        """Test manager initialization."""
        from src.hcode.memory.memory_manager import MemoryManager

        manager = MemoryManager(project_root=temp_project)

        assert manager.file_memory is not None
        assert manager.session_memory is not None
        assert manager.semantic_memory is not None

    def test_add_message(self, temp_project):
        """Test adding messages through manager."""
        from src.hcode.memory.memory_manager import MemoryManager

        manager = MemoryManager(project_root=temp_project)

        # Start fresh session
        manager.new_session()

        manager.add_message("user", "Hello, agent!")
        manager.add_message("assistant", "Hello! How can I help?")

        assert len(manager.session.messages) == 2

    def test_remember_recall(self, temp_project):
        """Test remember and recall functionality."""
        from src.hcode.memory.memory_manager import MemoryManager
        from src.hcode.memory.semantic_memory import MemoryType

        manager = MemoryManager(project_root=temp_project)

        # Remember something
        manager.remember(
            "This project uses FastAPI for the backend", memory_type=MemoryType.FACT, importance=0.8
        )

        # Recall it
        results = manager.recall("backend framework", top_k=1)

        assert len(results) > 0
        assert "fastapi" in results[0][0].content.lower()

    def test_get_context(self, temp_project):
        """Test getting context window."""
        from src.hcode.memory.memory_manager import MemoryManager

        manager = MemoryManager(project_root=temp_project)

        # Add some content
        manager.file_memory.update_memory("# Project Info\nA test project", scope="project")
        manager.add_message("user", "What is this project?")

        context = manager.get_context(query="project info")

        assert context is not None
        assert context.total_tokens > 0

    def test_build_system_context(self, temp_project):
        """Test building system context string."""
        from src.hcode.memory.memory_manager import MemoryManager

        manager = MemoryManager(project_root=temp_project)

        # Add project memory
        manager.file_memory.update_memory("# Project\nTest project info", scope="project")

        context = manager.build_system_context()

        assert "<agent-memory>" in context or "Project" in context

    def test_get_stats(self, temp_project):
        """Test getting manager statistics."""
        from src.hcode.memory.memory_manager import MemoryManager

        manager = MemoryManager(project_root=temp_project)

        stats = manager.get_stats()

        assert "project" in stats
        assert "file_memory" in stats
        assert "session" in stats
        assert "semantic_memory" in stats

    def test_context_manager(self, temp_project):
        """Test using manager as context manager."""
        from src.hcode.memory.memory_manager import MemoryManager

        with MemoryManager(project_root=temp_project) as manager:
            manager.new_session()  # Start fresh session
            manager.add_message("user", "Test message")
            assert len(manager.session.messages) == 1

        # Session should be saved on exit


class TestCLI:
    """Test CLI commands."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        (Path(temp_dir) / ".git").mkdir()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_create_parser(self):
        """Test CLI parser creation."""
        from src.hcode.memory.cli import create_parser

        parser = create_parser()
        assert parser is not None

        # Test parsing basic commands
        args = parser.parse_args(["status"])
        assert args.command == "status"

        args = parser.parse_args(["search", "test query"])
        assert args.command == "search"
        assert args.query == "test query"

    def test_init_command(self, temp_project):
        """Test init command functionality."""
        from src.hcode.memory.cli import cmd_init
        import argparse

        args = argparse.Namespace(path=str(temp_project), scope="project")

        # Should not raise
        cmd_init(args)

        # Check file was created
        assert (temp_project / "AGENT.md").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
