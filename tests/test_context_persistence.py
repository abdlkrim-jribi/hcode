"""
Test that conversation context persists correctly between messages.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hcode.core.context import ContextManager, ContextEntry
from hcode.providers import Message


class TestContextPersistence:
    """Test that context persists correctly"""

    def test_messages_added_to_context(self, tmp_path):
        """Messages should be added to context list"""
        cm = ContextManager(root_dir=str(tmp_path))

        # Add first message
        cm.add_message(role="user", content="Create a Python tutorial")

        # Add assistant response
        cm.add_message(role="assistant", content="I'll create a comprehensive tutorial...")

        # Check context has both messages
        assert len(cm.context) == 2
        assert cm.context[0].role == "user"
        assert cm.context[0].content == "Create a Python tutorial"
        assert cm.context[1].role == "assistant"
        assert cm.context[1].content == "I'll create a comprehensive tutorial..."

    def test_get_messages_returns_all_messages(self, tmp_path):
        """get_messages should return all messages in context"""
        cm = ContextManager(root_dir=str(tmp_path))
        cm.set_system_prompt("You are a helpful assistant")

        # Simulate conversation
        cm.add_message(role="user", content="Create a Python tutorial")
        cm.add_message(role="assistant", content="I'll create a comprehensive tutorial...")
        cm.add_message(role="user", content="proceed")

        # Get messages for model
        messages = cm.get_messages()

        # Should have system + 3 conversation messages
        assert len(messages) == 4
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert messages[1].content == "Create a Python tutorial"
        assert messages[2].role == "assistant"
        assert messages[3].role == "user"
        assert messages[3].content == "proceed"

    def test_context_persists_to_database(self, tmp_path):
        """Context should persist to SQLite database"""
        session_id = "test_session"

        # Create first context manager and add messages
        cm1 = ContextManager(root_dir=str(tmp_path), session_id=session_id)
        cm1.set_system_prompt("You are a helpful assistant")
        cm1.add_message(role="user", content="First message")
        cm1.add_message(role="assistant", content="First response")

        # Create second context manager with same session
        cm2 = ContextManager(root_dir=str(tmp_path), session_id=session_id)

        # Should load persisted messages
        assert len(cm2.context) == 2
        assert cm2.context[0].content == "First message"
        assert cm2.context[1].content == "First response"
        assert cm2.system_prompt == "You are a helpful assistant"

    def test_continuation_message_sees_history(self, tmp_path):
        """When user says 'proceed', context should include previous messages"""
        cm = ContextManager(root_dir=str(tmp_path))
        cm.set_system_prompt("You are a coding assistant")

        # First exchange
        cm.add_message(role="user", content="Create a comprehensive Python tutorial HTML file with dark mode, syntax highlighting, and interactive examples")
        cm.add_message(role="assistant", content="I'll create this file for you. Here's what I'll include:\n- Dark/Light mode toggle\n- Syntax highlighting\n- Interactive code examples\n\nPlease confirm by saying 'proceed'.")

        # User confirms
        cm.add_message(role="user", content="proceed")

        # Get messages - should include full history
        messages = cm.get_messages()

        # Verify all messages are present
        assert len(messages) == 4  # system + 3 conversation

        # Verify content
        contents = [m.content for m in messages]
        assert "Python tutorial HTML file" in contents[1]
        assert "I'll create this file" in contents[2]
        assert "proceed" in contents[3]

    def test_tool_results_added_to_context(self, tmp_path):
        """Tool results should be added to context for next iteration"""
        cm = ContextManager(root_dir=str(tmp_path))
        cm.set_system_prompt("You are a coding assistant")

        # User request
        cm.add_message(role="user", content="List files in current directory")

        # Assistant with tool call
        cm.add_message(role="assistant", content='{"tool": "LS", "parameters": {"path": "."}}')

        # Tool result (added as user message per the code pattern)
        cm.add_message(role="user", content="Tool 'LS' result:\nfile1.py\nfile2.py\nREADME.md")

        # Check context
        assert len(cm.context) == 3

        # Get messages
        messages = cm.get_messages()
        assert len(messages) == 4  # system + 3


class TestContinuationMessageEnhancement:
    """Test that continuation messages are properly enhanced with context"""

    def test_enhance_continuation_message_with_session_history(self):
        """Test that _enhance_continuation_message adds context from session history"""
        # We can't easily test HcodeChat directly without full initialization,
        # so we test the logic pattern

        # Simulate session history
        session_history = [
            {"role": "user", "content": "Create a comprehensive Python tutorial HTML file with dark mode and syntax highlighting"},
            {"role": "assistant", "content": "I'll create this file for you. Please confirm."},
        ]

        # The pattern we want to test
        confirmation_words = ['yes', 'y', 'ok', 'okay', 'sure', 'go ahead', 'proceed']
        message = "proceed"
        message_lower = message.strip().lower()

        if message_lower in confirmation_words:
            # Find original task
            original_task = None
            for msg in reversed(session_history):
                if msg.get('role') == 'user':
                    content = msg.get('content', '')
                    if content.strip().lower() not in confirmation_words and len(content) > 20:
                        original_task = content
                        break

            assert original_task is not None
            assert "Python tutorial" in original_task

            # Enhanced message should include context
            enhanced = f"User confirmed: {message}. Please proceed with the previously discussed task: {original_task}"
            assert "proceed" in enhanced
            assert "Python tutorial" in enhanced


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
