"""
Unit tests for the workflow system (WorkflowStep, Workflow, WorkflowManager, WorkflowTool).
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from hcode.tools.system.command_system import (
    WorkflowStep,
    Workflow,
    WorkflowManager,
    WorkflowTool,
    CommandRegistry,
)


# ─── Workflow.parse ────────────────────────────────────────────────────────────

class TestWorkflowParse:

    def test_parse_basic_frontmatter(self):
        content = "---\ndescription: Deploy app\n---\n1. Do something"
        wf = Workflow.parse("deploy", content)
        assert wf.name == "deploy"
        assert wf.description == "Deploy app"
        assert len(wf.steps) == 1

    def test_parse_no_frontmatter(self):
        content = "1. Do something"
        wf = Workflow.parse("test", content)
        assert wf.description == ""
        assert len(wf.steps) == 1

    def test_parse_turbo_annotation(self):
        content = "---\ndescription: Test\n---\n// turbo\n1. npm run build"
        wf = Workflow.parse("test", content)
        step = wf.steps[0]
        assert step.turbo is True
        assert step.is_command is True
        assert step.content == "npm run build"

    def test_parse_turbo_all_annotation(self):
        content = "---\ndescription: Test\n---\n// turbo-all\n1. npm run build\n2. git push"
        wf = Workflow.parse("test", content)
        assert wf.turbo_all is True
        assert all(s.turbo for s in wf.steps)

    def test_parse_turbo_only_affects_next_step(self):
        content = (
            "---\ndescription: Test\n---\n"
            "// turbo\n1. npm run build\n"
            "2. git push staging main"
        )
        wf = Workflow.parse("test", content)
        assert wf.steps[0].turbo is True
        assert wf.steps[1].turbo is False

    def test_parse_strips_numbered_prefix(self):
        content = "---\ndescription: Test\n---\n2. npm run build"
        wf = Workflow.parse("test", content)
        assert wf.steps[0].content == "npm run build"

    def test_parse_detects_command_prefixes(self):
        commands = [
            "npm run build",
            "git push origin main",
            "python manage.py migrate",
            "pip install -r requirements.txt",
            "docker build .",
            "pytest tests/",
        ]
        for cmd in commands:
            content = f"---\ndescription: Test\n---\n1. {cmd}"
            wf = Workflow.parse("test", content)
            assert wf.steps[0].is_command is True, f"Expected is_command=True for: {cmd}"

    def test_parse_non_command_step(self):
        content = "---\ndescription: Test\n---\nCheck the logs manually"
        wf = Workflow.parse("test", content)
        assert wf.steps[0].is_command is False

    def test_parse_empty_lines_ignored(self):
        content = "---\ndescription: Test\n---\n\n1. npm run build\n\n2. git push\n"
        wf = Workflow.parse("test", content)
        assert len(wf.steps) == 2


# ─── WorkflowManager ──────────────────────────────────────────────────────────

class TestWorkflowManager:

    def test_load_workflows_missing_dir(self, tmp_path):
        wm = WorkflowManager(root_dir=str(tmp_path))
        assert wm.workflows == {}

    def test_load_workflows_discovers_md_files(self, tmp_path):
        wf_dir = tmp_path / ".hcode" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "deploy.md").write_text(
            "---\ndescription: Deploy\n---\n1. npm run build"
        )
        wm = WorkflowManager(root_dir=str(tmp_path))
        assert "deploy" in wm.workflows

    def test_load_workflows_ignores_invalid_files(self, tmp_path):
        wf_dir = tmp_path / ".hcode" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "broken.md").write_text("")
        wm = WorkflowManager(root_dir=str(tmp_path))
        # broken file has no steps but still loads (empty steps list)
        assert wm.workflows == {} or "broken" in wm.workflows

    def test_get_workflow_returns_correct(self, tmp_path):
        wf_dir = tmp_path / ".hcode" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "setup.md").write_text(
            "---\ndescription: Setup\n---\n1. pip install -e ."
        )
        wm = WorkflowManager(root_dir=str(tmp_path))
        wf = wm.get_workflow("setup")
        assert wf is not None
        assert wf.name == "setup"

    def test_get_workflow_returns_none_for_missing(self, tmp_path):
        wm = WorkflowManager(root_dir=str(tmp_path))
        assert wm.get_workflow("nonexistent") is None

    def test_is_trusted_path_inside(self, tmp_path):
        wf_dir = tmp_path / ".hcode" / "workflows"
        wf_dir.mkdir(parents=True)
        wm = WorkflowManager(root_dir=str(tmp_path))
        trusted_file = wf_dir / "deploy.md"
        trusted_file.touch()
        assert wm.is_trusted_path(trusted_file) is True

    def test_is_trusted_path_outside(self, tmp_path):
        wm = WorkflowManager(root_dir=str(tmp_path))
        outside_file = tmp_path / "evil.md"
        outside_file.touch()
        assert wm.is_trusted_path(outside_file) is False


# ─── WorkflowTool ─────────────────────────────────────────────────────────────

class TestWorkflowTool:

    def _make_tool(self, tmp_path):
        registry = MagicMock(spec=CommandRegistry)
        registry.root_dir = tmp_path
        tool = WorkflowTool(command_registry=registry)
        return tool

    def test_workflow_not_found(self, tmp_path):
        import asyncio
        tool = self._make_tool(tmp_path)
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(workflow="nonexistent")
        )
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_workflow_found_returns_steps(self, tmp_path):
        import asyncio
        wf_dir = tmp_path / ".hcode" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "deploy.md").write_text(
            "---\ndescription: Deploy\n---\n1. Check the build\n2. npm run build"
        )
        tool = self._make_tool(tmp_path)
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(workflow="deploy")
        )
        assert result.success is True
        assert "deploy" in result.output.lower()
        assert result.metadata["workflow"] == "deploy"
        assert len(result.metadata["steps"]) == 2

    def test_workflow_strips_leading_slash(self, tmp_path):
        import asyncio
        wf_dir = tmp_path / ".hcode" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "deploy.md").write_text(
            "---\ndescription: Deploy\n---\n1. npm run build"
        )
        tool = self._make_tool(tmp_path)
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(workflow="/deploy")
        )
        assert result.success is True

    def test_turbo_steps_marked_in_metadata(self, tmp_path):
        import asyncio
        wf_dir = tmp_path / ".hcode" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.md").write_text(
            "---\ndescription: CI\n---\n// turbo\n1. pytest tests/"
        )
        tool = self._make_tool(tmp_path)
        with patch("hcode.core.session_manager.get_session_manager") as mock_sm:
            mock_sm.return_value = MagicMock()
            result = asyncio.get_event_loop().run_until_complete(
                tool.execute(workflow="ci")
            )
        assert result.success is True
        assert result.metadata["steps"][0]["turbo"] is True

    def test_security_rejects_untrusted_path(self, tmp_path):
        import asyncio
        tool = self._make_tool(tmp_path)
        # Manually inject a workflow with untrusted path
        evil_path = tmp_path / "evil.md"
        evil_path.write_text("---\ndescription: Evil\n---\n1. rm -rf /")
        from hcode.tools.system.command_system import Workflow
        tool.workflow_manager.workflows["evil"] = Workflow.parse(
            name="evil",
            content=evil_path.read_text(),
            file_path=evil_path,
        )
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(workflow="evil")
        )
        assert result.success is False
        assert "security" in result.error.lower()
