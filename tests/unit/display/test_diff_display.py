"""Tests for diff display and change proposal functionality in diff_tools.py."""

import pytest
from hcode.tools.files.diff_tools import (
    DiffLine,
    DiffHunk,
    ChangeProposal,
    ChangeOperation,
    ChangeStatus,
    DiffPreviewTool,
)


def test_diff_line_creation():
    line = DiffLine(line_number_old=1, line_number_new=1, content="hello", change_type="unchanged")
    assert line.line_number_old == 1
    assert line.line_number_new == 1
    assert line.content == "hello"
    assert line.change_type == "unchanged"


def test_diff_line_addition():
    line = DiffLine(line_number_old=None, line_number_new=5, content="new line", change_type="added")
    assert line.line_number_old is None
    assert line.line_number_new == 5
    assert line.change_type == "added"


def test_diff_line_removal():
    line = DiffLine(line_number_old=3, line_number_new=None, content="old line", change_type="removed")
    assert line.line_number_old == 3
    assert line.line_number_new is None
    assert line.change_type == "removed"


def test_diff_line_to_dict():
    line = DiffLine(line_number_old=1, line_number_new=2, content="text", change_type="context")
    d = line.to_dict()
    assert d["line_number_old"] == 1
    assert d["line_number_new"] == 2
    assert d["content"] == "text"
    assert d["change_type"] == "context"


def test_change_proposal_compute_diff_addition():
    proposal = ChangeProposal(
        file_path="test.py",
        operation=ChangeOperation.EDIT,
        old_content="line1\nline2\n",
        new_content="line1\nline2\nline3\n",
    )
    proposal.compute_diff()
    assert proposal.additions >= 1
    assert proposal.deletions == 0
    assert proposal.unified_diff != ""


def test_change_proposal_compute_diff_deletion():
    proposal = ChangeProposal(
        file_path="test.py",
        operation=ChangeOperation.EDIT,
        old_content="line1\nline2\nline3\n",
        new_content="line1\nline3\n",
    )
    proposal.compute_diff()
    assert proposal.deletions >= 1
    assert proposal.additions == 0


def test_change_proposal_compute_diff_modification():
    proposal = ChangeProposal(
        file_path="test.py",
        operation=ChangeOperation.EDIT,
        old_content="line1\nold text\nline3\n",
        new_content="line1\nnew text\nline3\n",
    )
    proposal.compute_diff()
    assert proposal.additions >= 1
    assert proposal.deletions >= 1


def test_change_proposal_no_changes():
    content = "line1\nline2\n"
    proposal = ChangeProposal(
        file_path="test.py",
        operation=ChangeOperation.EDIT,
        old_content=content,
        new_content=content,
    )
    proposal.compute_diff()
    assert proposal.additions == 0
    assert proposal.deletions == 0
    assert proposal.hunks == []


def test_change_proposal_get_summary():
    proposal = ChangeProposal(
        file_path="myfile.py",
        operation=ChangeOperation.EDIT,
        old_content="old\n",
        new_content="new\n",
    )
    proposal.compute_diff()
    summary = proposal.get_summary()
    assert "myfile.py" in summary
    assert "Edit" in summary or "edit" in summary.lower()


def test_change_proposal_has_critical_warnings_false():
    proposal = ChangeProposal(
        file_path="test.py",
        operation=ChangeOperation.EDIT,
        old_content="x = 1\n",
        new_content="x = 2\n",
    )
    proposal.analyze_safety()
    assert proposal.has_critical_warnings() is False


def test_change_proposal_initial_status():
    proposal = ChangeProposal(file_path="test.py")
    assert proposal.status == ChangeStatus.PENDING


def test_change_operation_values():
    assert ChangeOperation.EDIT.value == "edit"
    assert ChangeOperation.WRITE.value == "write"
    assert ChangeOperation.CREATE.value == "create"


def test_change_status_values():
    assert ChangeStatus.PENDING.value == "pending"
    assert ChangeStatus.APPLIED.value == "applied"
    assert ChangeStatus.REJECTED.value == "rejected"
    assert ChangeStatus.FAILED.value == "failed"


def test_diff_preview_tool_creation():
    tool = DiffPreviewTool()
    assert tool.name == "DiffPreview"
    assert tool.get_description() != ""
    assert len(tool.get_parameters()) > 0
