"""
Sanity Check: Memory Components Tests.

Tests the basic functionality of memory system components.
"""
import pytest
import tempfile
from pathlib import Path


class TestMemoryConfig:
    """Test memory config component."""

    def test_memory_config_import(self):
        """Test memory config module imports."""
        from hcode.memory.config import MemoryConfig, config
        assert MemoryConfig is not None
        assert config is not None

    def test_memory_config_defaults(self):
        """Test MemoryConfig has default values."""
        from hcode.memory.config import MemoryConfig
        cfg = MemoryConfig()
        assert cfg is not None
        assert hasattr(cfg, 'max_context_tokens')
        assert hasattr(cfg, 'extract_facts')


class TestFileMemoryComponent:
    """Test file memory component."""

    def test_file_memory_import(self):
        """Test file_memory module imports."""
        from hcode.memory.file_memory import FileMemory
        assert FileMemory is not None

    def test_file_memory_instantiation(self):
        """Test FileMemory can be instantiated."""
        from hcode.memory.file_memory import FileMemory
        with tempfile.TemporaryDirectory() as tmpdir:
            fm = FileMemory(project_root=Path(tmpdir))
            assert fm is not None

    def test_file_memory_get_context(self):
        """Test FileMemory can get combined context."""
        from hcode.memory.file_memory import FileMemory
        with tempfile.TemporaryDirectory() as tmpdir:
            fm = FileMemory(project_root=Path(tmpdir))
            context = fm.get_combined_context()
            assert isinstance(context, str)


class TestSessionMemoryComponent:
    """Test session memory component."""

    def test_session_memory_import(self):
        """Test session_memory module imports."""
        from hcode.memory.session_memory import SessionMemory, Session, Message
        assert SessionMemory is not None
        assert Session is not None
        assert Message is not None

    def test_session_memory_instantiation(self):
        """Test SessionMemory can be instantiated."""
        from hcode.memory.session_memory import SessionMemory
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionMemory(project_root=Path(tmpdir))
            assert sm is not None

    def test_session_memory_create_session(self):
        """Test SessionMemory can create a session."""
        from hcode.memory.session_memory import SessionMemory
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionMemory(project_root=Path(tmpdir))
            session = sm.create_session()
            assert session is not None
            assert hasattr(session, 'session_id')


class TestSemanticMemoryComponent:
    """Test semantic memory component."""

    def test_semantic_memory_import(self):
        """Test semantic_memory module imports."""
        from hcode.memory.semantic_memory import SemanticMemory, Memory, MemoryType
        assert SemanticMemory is not None
        assert Memory is not None
        assert MemoryType is not None

    def test_memory_type_enum(self):
        """Test MemoryType enum has expected values."""
        from hcode.memory.semantic_memory import MemoryType
        assert hasattr(MemoryType, 'FACT')
        assert hasattr(MemoryType, 'PREFERENCE')
        assert hasattr(MemoryType, 'CONTEXT')


class TestMemoryManagerComponent:
    """Test memory manager component."""

    def test_memory_manager_import(self):
        """Test memory_manager module imports."""
        from hcode.memory.memory_manager import MemoryManager, ContextWindow
        assert MemoryManager is not None
        assert ContextWindow is not None

    def test_memory_manager_instantiation(self):
        """Test MemoryManager can be instantiated."""
        from hcode.memory.memory_manager import MemoryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            mm = MemoryManager(project_root=Path(tmpdir))
            assert mm is not None

    def test_memory_manager_get_stats(self):
        """Test MemoryManager can get stats."""
        from hcode.memory.memory_manager import MemoryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            mm = MemoryManager(project_root=Path(tmpdir))
            stats = mm.get_stats()
            assert isinstance(stats, dict)
            assert 'project' in stats
            assert 'session' in stats

    def test_context_manager_protocol(self):
        """Test MemoryManager supports context manager protocol."""
        from hcode.memory.memory_manager import MemoryManager
        with tempfile.TemporaryDirectory() as tmpdir:
            with MemoryManager(project_root=Path(tmpdir)) as mm:
                assert mm is not None


class TestEmbeddingsComponent:
    """Test embeddings component."""

    def test_embeddings_import(self):
        """Test embeddings module imports."""
        from hcode.memory import embeddings
        assert embeddings is not None


class TestMemoryCLIComponent:
    """Test memory CLI component."""

    def test_memory_cli_import(self):
        """Test memory cli module imports."""
        from hcode.memory import cli
        assert cli is not None
