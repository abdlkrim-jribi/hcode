import pytest
from hcode.core.classification.task_classifier import TaskClassifier
from hcode.core.classification import TaskComplexity


class TestIsTrivial:
    def setup_method(self):
        self.classifier = TaskClassifier()

    def test_mcp_call_is_trivial(self):
        assert self.classifier.is_trivial("call mcp_github-local_list_commits with owner=x repo=y") is True

    def test_use_mcp_is_trivial(self):
        assert self.classifier.is_trivial("use mcp_github to list branches") is True

    def test_list_branches_is_trivial(self):
        assert self.classifier.is_trivial("list branches") is True

    def test_list_commits_is_trivial(self):
        assert self.classifier.is_trivial("list commits in this repo") is True

    def test_get_file_is_trivial(self):
        assert self.classifier.is_trivial("get file src/main.py") is True

    def test_complex_task_not_trivial(self):
        assert self.classifier.is_trivial("implement a full authentication system with JWT") is False

    def test_refactor_not_trivial(self):
        assert self.classifier.is_trivial("refactor the entire codebase to use async") is False

    def test_classify_returns_trivial(self):
        result = self.classifier.classify("call mcp_github-local_list_commits with owner=x")
        assert result == TaskComplexity.TRIVIAL

    def test_classify_complex_still_works(self):
        result = self.classifier.classify("implement a full REST API with authentication")
        assert result != TaskComplexity.TRIVIAL
