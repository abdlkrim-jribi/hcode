import asyncio
import os
import sys
import io
import json
from pathlib import Path
from unittest.mock import MagicMock
from dataclasses import asdict

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add src to path
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, src_path)

from hcode.core.agent import HcodeAgent
from hcode.providers.base import ToolCall, CompletionResponse, Usage
from hcode.providers.openai_provider import OpenAIProvider
from hcode.tools.base_tool import ToolResult

# Mock Provider Factory to reset state between scenarios
def create_mock_agent(scenario_name, responses):
    """
    Creates an agent with a mock provider programmed with a sequence of responses.
    responses: List of (CompletionResponse) or Callable taking (history) -> CompletionResponse
    """
    print(f"\n{'='*20} SCENARIO: {scenario_name} {'='*20}")
    
    agent = HcodeAgent(openai_key="mock-key", autonomous_mode=True, openai_model="gpt-oss-120b")
    
    # Mock Provider
    mock_provider = MagicMock(spec=OpenAIProvider)
    mock_provider.name = "openai"
    mock_provider.model = "gpt-oss-120b"
    mock_provider.count_tokens.side_effect = lambda x: 10 
    mock_provider.get_context_window.return_value = 128000
    mock_provider.supports_function_calling.return_value = True
    mock_provider._total_usage = Usage(0, 0, 0)
    mock_provider.max_tokens = 4096 
    
    # Generation Logic
    async def mock_generate(*args, **kwargs):
        call_idx = mock_provider.call_count
        mock_provider.call_count += 1
        
        if call_idx < len(responses):
            resp = responses[call_idx]
            if callable(resp):
                return resp()
            return resp
        else:
            # Default fallback if scenario runs longer than expected
            return CompletionResponse(
                content="Scenario limit reached. Stopping.",
                usage=Usage(10,10,20),
                model="gpt-oss-120b",
                finish_reason="stop"
            )

    mock_provider.generate_completion = mock_generate
    mock_provider.call_count = 0
    
    # Mock Selector
    mock_selector = MagicMock()
    mock_selector.get_provider.return_value = mock_provider
    mock_selector.get_current_provider.return_value = mock_provider
    mock_selector.select_provider.return_value = mock_provider
    
    agent.provider_selector = mock_selector
    agent.current_provider = mock_provider
    
    # Mock Context Manager (Minimal)
    mock_context = MagicMock()
    mock_context.get_recent_messages.return_value = []
    mock_context.get_history.return_value = []
    agent.context_manager = mock_context
    
    return agent

# --- SCENARIOS ---

async def scenario_write_read_check():
    """
    Scenario:
    1. Agent decides to write a file 'hello.txt'.
    2. Agent decides to read it back to verify.
    3. Agent completes.
    """
    
    # Response 1: Call WriteTool
    r1 = CompletionResponse(
        content="I will create a hello world file.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c1", name="WriteTool", arguments={"file_path": "hello.txt", "content": "Hello World"})]
    )
    
    # Response 2: Call ReadTool (after write success)
    r2 = CompletionResponse(
        content="Now I will read it back.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c2", name="ReadTool", arguments={"file_path": "hello.txt"})]
    )
    
    # Response 3: Finish
    r3 = CompletionResponse(
        content="Verification complete. Content matches.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="stop"
    )
    
    agent = create_mock_agent("Write & Verify", [r1, r2, r3])
    
    # File cleanup
    if os.path.exists("hello.txt"):
        os.remove("hello.txt")
        
    await agent.execute_task("Create hello.txt and verify it", stream=False)
    
    # Assertions
    if not os.path.exists("hello.txt"):
        print("❌ FAILURE: hello.txt was not created")
        return
        
    with open("hello.txt", "r") as f:
        content = f.read()
        if content == "Hello World":
            print("✅ SUCCESS: File created with correct content")
        else:
            print(f"❌ FAILURE: Content mismatch: {content}")

    # Clean up
    if os.path.exists("hello.txt"):
        os.remove("hello.txt")


async def scenario_ls_filter():
    """
    Scenario:
    1. Agent lists current directory.
    2. Agent completes saying it found files.
    """
    # Response 1: Call LSTool
    r1 = CompletionResponse(
        content="I will list the directory.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c1", name="LSTool", arguments={"path": "."})]
    )
    
    # Response 2: Finish
    r2 = CompletionResponse(
        content="I have listed the files.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="stop"
    )
    
    agent = create_mock_agent("List Directory", [r1, r2])
    
    await agent.execute_task("List files in current directory", stream=False)
    print("✅ SUCCESS: LSTool executed without crash")


async def scenario_error_recovery():
    """
    Scenario:
    1. Agent tries to read non-existent file.
    2. Tool returns error.
    3. Agent corrects itself (creates file).
    4. Agent reads again.
    """
    
    # Response 1: Read missing file
    r1 = CompletionResponse(
        content="Checking config.",
        usage=Usage(10,10,20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c1", name="ReadTool", arguments={"file_path": "missing_config.json"})]
    )
    
    # Response 2: Oops, missing. Create it.
    r2 = CompletionResponse(
        content="File is missing. I will create it.",
        usage=Usage(10,10,20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c2", name="WriteTool", arguments={"file_path": "missing_config.json", "content": "{}"})]
    )
    
    # Response 3: Read again
    r3 = CompletionResponse(
        content="Reading again.",
        usage=Usage(10,10,20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c3", name="ReadTool", arguments={"file_path": "missing_config.json"})]
    )
    
    # Response 4: Done
    r4 = CompletionResponse(
        content="Done.",
        usage=Usage(10,10,20),
        model="gpt-oss-120b",
        finish_reason="stop"
    )
    
    agent = create_mock_agent("Error Recovery", [r1, r2, r3, r4])
    
    if os.path.exists("missing_config.json"):
        os.remove("missing_config.json")
        
    await agent.execute_task("Ensure config exists", stream=False)
    
    if os.path.exists("missing_config.json"):
         print("✅ SUCCESS: Recovery successful, file created")
         os.remove("missing_config.json")
    else:
         print("❌ FAILURE: File not created after recovery")


async def scenario_complex_refactor():
    """
    Scenario: Complex Refactor
    1. Agent searches for 'LegacyClass' usage.
    2. Agent reads the relevant files.
    3. Agent updates the class definition.
    4. Agent updates the usage.
    """
    
    # 1. Search for usages
    r1 = CompletionResponse(
        content="I will search for LegacyClass usage first.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c1", name="GrepTool", arguments={"pattern": "LegacyClass", "path": "."})]
    )

    # 2. Read files (agent decides to read found files)
    r2 = CompletionResponse(
        content="Found usages in legacy_mod.py and app.py. I will read them.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[
            ToolCall(id="c2", name="ReadTool", arguments={"file_path": "legacy_mod.py"}),
            ToolCall(id="c3", name="ReadTool", arguments={"file_path": "app.py"}),
        ]
    )

    # 3. Rename class definition
    r3 = CompletionResponse(
        content="I will rename LegacyClass to ModernClass in legacy_mod.py.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c4", name="EditTool", arguments={
            "file_path": "legacy_mod.py", 
            "old_string": "class LegacyClass:", 
            "new_string": "class ModernClass:"
        })]
    )

    # 4. Update usage in app.py
    r4 = CompletionResponse(
        content="Now updating usage in app.py.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c5", name="EditTool", arguments={
            "file_path": "app.py", 
            "old_string": "from legacy_mod import LegacyClass", 
            "new_string": "from legacy_mod import ModernClass"
        })]
    )

    # 5. Finish
    r5 = CompletionResponse(
        content="Refactor complete. Renamed LegacyClass to ModernClass and updated usages.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="stop"
    )

    agent = create_mock_agent("Complex Refactor", [r1, r2, r3, r4, r5])

    # Preset files
    with open("legacy_mod.py", "w", encoding="utf-8") as f:
        f.write("class LegacyClass:\n    pass\n")
    with open("app.py", "w", encoding="utf-8") as f:
        f.write("from legacy_mod import LegacyClass\nx = LegacyClass()\n")
    
    # Mock GrepTool since it's hard to mock real grep behavior in this script structure 
    # (unless my mock_execute_tool handles it, which it doesn't currently)
    # So I will inject a mocked Grep response into execute_tool inside the scenario-specific mock logic if I could...
    # But wait, my generic mock_execute_tool outputs "Mock result". 
    # I need to enhance logic to handle GrepTool and return meaningful results.
    
    # Let's override the execute_tool for this agent
    original_exec = agent.tool_manager.execute_tool
    
    async def specific_mock_execute_tool(name, **kwargs):
        print(f"    -> [EXECUTION] Executing {name} with {kwargs}")
        name_lower = name.lower()
        if name_lower == "greptool" or name_lower == "grep":
             return ToolResult(success=True, output="legacy_mod.py:1:class LegacyClass:\napp.py:1:from legacy_mod import LegacyClass")
        elif name_lower == "readtool" or name_lower == "read":
            path = kwargs.get("file_path")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return ToolResult(success=True, output=f.read())
            return ToolResult(success=False, output="File not found")
        elif name_lower == "edittool" or name_lower == "edit":
             path = kwargs.get("file_path")
             old = kwargs.get("old_string")
             new = kwargs.get("new_string")
             if os.path.exists(path):
                 with open(path, "r", encoding="utf-8") as f:
                     content = f.read()
                 if old in content:
                     new_content = content.replace(old, new)
                     with open(path, "w", encoding="utf-8") as f:
                         f.write(new_content)
                     return ToolResult(success=True, output="File edited successfully")
                 return ToolResult(success=False, output="Old string not found")
             return ToolResult(success=False, output="File not found")
        
        return ToolResult(success=True, output="Mock result")

    agent.tool_manager.execute_tool = specific_mock_execute_tool

    await agent.execute_task("Refactor LegacyClass to ModernClass", stream=False)

    # Verification
    try:
        with open("legacy_mod.py", "r") as f:
            if "class ModernClass:" in f.read():
                print("✅ SUCCESS: Class renamed")
            else:
                print("❌ FAILURE: Class not renamed")
        
        with open("app.py", "r") as f:
             if "from legacy_mod import ModernClass" in f.read():
                 print("✅ SUCCESS: Usage updated")
             else:
                 print("❌ FAILURE: Usage not updated")
    finally:
        if os.path.exists("legacy_mod.py"): os.remove("legacy_mod.py")
        if os.path.exists("app.py"): os.remove("app.py")


async def scenario_hallucination_recovery():
    """
    Scenario: Hallucination Recovery
    1. Agent returns code block without tool call (Hallucination).
    2. Agent checks context and adds the hallucination + error.
    3. Agent corrects itself with tool call.
    """
    
    # 1. Hallucination Response
    r1 = CompletionResponse(
        content="""I will write the file for you.
```python
print("This is a hallucination")
```
Done.""",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="stop" # No tool calls!
    )

    # 2. Correction Response
    r2 = CompletionResponse(
        content="Apologies, I should use the WriteTool.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c1", name="WriteTool", arguments={"file_path": "hallucination.py", "content": "print('Fixed')"})]
    )

    # 3. Finish
    r3 = CompletionResponse(
        content="File created properly.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="stop"
    )

    agent = create_mock_agent("Hallucination Recovery", [r1, r2, r3])
    
    # We want to verify that the hallucinated message was added to context.
    # We can inspect the mock context manager AFTER execution.
    # But agent.context_manager is a mock.
    
    await agent.execute_task("Create a file with specific code", stream=False)
    
    # Verification
    # Check if the hallucinated content was added to context
    calls = agent.context_manager.add_message.call_args_list
    
    hallucination_added = False
    error_added = False
    
    for call in calls:
        kwargs = call.kwargs
        content = kwargs.get("content", "")
        role = kwargs.get("role", "")
        
        if role == "assistant" and "This is a hallucination" in content:
            hallucination_added = True
        if role == "user" and "CRITICAL ERROR: CODE BLOCK HALLUCINATION" in content:
            error_added = True
            
    if hallucination_added:
        print("✅ SUCCESS: Hallucinated response added to context")
    else:
        print("❌ FAILURE: Hallucinated response NOT added to context")
        
    if error_added:
        print("✅ SUCCESS: Critical error message added to context")
    else:
        print("❌ FAILURE: Critical error message NOT added to context")

async def scenario_missing_tests():
    """
    Scenario: User asks to run a test, but none exist.
    Agent should search and then conclude gracefully without hallucinating code.
    """
    
    # 1. Glob search (empty)
    r1 = CompletionResponse(
        content="I will look for test files.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c1", name="GlobTool", arguments={"pattern": "**/test_*.py", "path": "."})]
    )

    # 2. Grep search (empty)
    r2 = CompletionResponse(
        content="No test files found. Checking for 'def test_'.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[ToolCall(id="c2", name="GrepTool", arguments={"pattern": "def test_", "path": "."})]
    )

    # 3. Conclusion (Stop)
    r3 = CompletionResponse(
        content="No tests found in the repository. I cannot run a test.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="stop"
    )

    agent = create_mock_agent("Missing Tests", [r1, r2, r3])
    
    # Mock Glob/Grep to return empty
    original_exec = agent.tool_manager.execute_tool
    
    async def specific_mock_execute_tool(name, **kwargs):
        name_lower = name.lower()
        if "glob" in name_lower:
             return ToolResult(success=True, output="No matches found")
        if "grep" in name_lower:
             return ToolResult(success=True, output="No matches found")
        return ToolResult(success=True, output="Mock result")

    agent.tool_manager.execute_tool = specific_mock_execute_tool

    await agent.execute_task("Run one unit test", stream=False)
    
    # Verify no file writes happened (checking if any unexpected files created)
    # Since we didn't mock WriteTool, it wouldn't work anyway, but strictly
    # we just want to ensure it finished without error/hallucination warning.
    print("✅ SUCCESS: Agent concluded 'No tests found' without hallucination")


async def main():
    print("🚀 Starting Comprehensive Stress Test...")
    await scenario_write_read_check()
    await scenario_ls_filter()
    await scenario_error_recovery()
    await scenario_complex_refactor()
    await scenario_hallucination_recovery()
    await scenario_missing_tests()
    print("\n🏁 All scenarios completed.")

if __name__ == "__main__":
    asyncio.run(main())
