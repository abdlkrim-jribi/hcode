"""
Tests for folder-based skills system.

Verifies that CommandRegistry discovers folder-based skills (.hcode/skills/<name>/SKILL.md),
supports legacy flat-file skills, handles edge cases gracefully, and that SkillTool
exposes the skill_dir in metadata.
"""

import pytest
import sys
import os
import importlib.util
from pathlib import Path

# Direct-load modules via importlib.util to bypass the hcode.__init__ chain
# which pulls the full core/tools tree and may hit missing optional modules.
_SRC = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))


def _load_module(module_name: str, file_path: str):
    """Load a single Python module from file, registering it in sys.modules."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# 1) base_tool (dependency of command_system)
_base_tool = _load_module(
    "hcode.tools.base.base_tool",
    os.path.join(_SRC, "hcode", "tools", "base", "base_tool.py"),
)

# 2) command_system
_cmd_sys = _load_module(
    "hcode.tools.system.command_system",
    os.path.join(_SRC, "hcode", "tools", "system", "command_system.py"),
)

CommandRegistry = _cmd_sys.CommandRegistry
Skill = _cmd_sys.Skill
SkillTool = _cmd_sys.SkillTool


def _create_skill_file(path: Path, description: str, category: str, prompt: str):
    """Helper to create a skill .md file with valid frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ndescription: {description}\ncategory: {category}\n---\n{prompt}",
        encoding="utf-8",
    )


class TestFolderSkillDiscovery:
    """Test 1: Folder-based skill is discovered with correct attributes."""

    def test_folder_skill_discovery(self, tmp_path):
        skill_dir = tmp_path / ".hcode" / "skills" / "my-skill"
        _create_skill_file(
            skill_dir / "SKILL.md",
            description="A test skill",
            category="testing",
            prompt="Do the thing",
        )

        registry = CommandRegistry(root_dir=str(tmp_path))

        skill = registry.get_skill("my-skill")
        assert skill is not None
        assert skill.name == "my-skill"
        assert skill.description == "A test skill"
        assert skill.category == "testing"
        assert skill.folder_path is not None
        assert skill.folder_path == skill_dir.resolve()


class TestLegacyFlatFile:
    """Test 2: Legacy flat .md files still load with folder_path=None."""

    def test_legacy_flat_file_still_works(self, tmp_path):
        skills_dir = tmp_path / ".hcode" / "skills"
        _create_skill_file(
            skills_dir / "hello.md",
            description="A greeting skill",
            category="communication",
            prompt="Hello {name}!",
        )

        registry = CommandRegistry(root_dir=str(tmp_path))

        skill = registry.get_skill("hello")
        assert skill is not None
        assert skill.name == "hello"
        assert skill.description == "A greeting skill"
        assert skill.folder_path is None


class TestFolderPriority:
    """Test 3: Folder-based skill takes priority over flat file with same name."""

    def test_folder_priority_over_flat_file(self, tmp_path):
        skills_dir = tmp_path / ".hcode" / "skills"

        # Create folder-based skill
        _create_skill_file(
            skills_dir / "test" / "SKILL.md",
            description="folder version",
            category="testing",
            prompt="I am the folder skill",
        )

        # Create flat-file with same name
        _create_skill_file(
            skills_dir / "test.md",
            description="flat version",
            category="testing",
            prompt="I am the flat skill",
        )

        registry = CommandRegistry(root_dir=str(tmp_path))

        skill = registry.get_skill("test")
        assert skill is not None
        assert skill.description == "folder version"
        assert skill.folder_path is not None


class TestSkillDirPlaceholder:
    """Test 4: {skill_dir} placeholder is resolved to the absolute folder path."""

    def test_skill_dir_placeholder_injection(self, tmp_path):
        skill_dir = tmp_path / ".hcode" / "skills" / "my-skill"
        _create_skill_file(
            skill_dir / "SKILL.md",
            description="test",
            category="testing",
            prompt="Scripts at {skill_dir}/scripts/",
        )

        registry = CommandRegistry(root_dir=str(tmp_path))

        skill = registry.get_skill("my-skill")
        result = skill.execute()

        expected_path = str(skill_dir.resolve())
        assert expected_path in result
        assert "{skill_dir}" not in result


class TestMissingSkillMd:
    """Test 5: Folder without SKILL.md is silently skipped."""

    def test_missing_skill_md_skipped(self, tmp_path):
        # Create a folder with no SKILL.md
        empty_dir = tmp_path / ".hcode" / "skills" / "no-skill"
        empty_dir.mkdir(parents=True)
        (empty_dir / "README.md").write_text("not a skill", encoding="utf-8")

        registry = CommandRegistry(root_dir=str(tmp_path))

        assert registry.get_skill("no-skill") is None
        assert len(registry.list_skills()) == 0


class TestInvalidFrontmatter:
    """Test 6: Broken YAML frontmatter is gracefully skipped."""

    def test_invalid_frontmatter_skipped(self, tmp_path):
        skill_dir = tmp_path / ".hcode" / "skills" / "broken"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n: invalid: yaml: [broken\n---\nsome prompt",
            encoding="utf-8",
        )

        registry = CommandRegistry(root_dir=str(tmp_path))

        assert registry.get_skill("broken") is None
        assert len(registry.list_skills()) == 0


class TestEmptySkillsDir:
    """Test 7: Empty .hcode/skills/ directory causes no crash."""

    def test_empty_skills_dir(self, tmp_path):
        skills_dir = tmp_path / ".hcode" / "skills"
        skills_dir.mkdir(parents=True)

        registry = CommandRegistry(root_dir=str(tmp_path))

        assert len(registry.list_skills()) == 0


class TestSkillToolMetadata:
    """Test 8: SkillTool.execute() metadata includes skill_dir for folder-based skills."""

    @pytest.mark.asyncio
    async def test_skill_tool_metadata_includes_dir(self, tmp_path):
        skill_dir = tmp_path / ".hcode" / "skills" / "my-skill"
        _create_skill_file(
            skill_dir / "SKILL.md",
            description="test",
            category="testing",
            prompt="Hello from skill",
        )

        registry = CommandRegistry(root_dir=str(tmp_path))
        tool = SkillTool(registry)  # No agent_orchestrator → returns prompt

        result = await tool.execute(skill="my-skill")

        assert result.success is True
        assert result.metadata is not None
        assert result.metadata["skill_dir"] == str(skill_dir.resolve())
        assert result.metadata["skill"] == "my-skill"
        assert result.metadata["category"] == "testing"
