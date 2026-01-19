import asyncio
import os
import sys
import io
from pathlib import Path
from unittest.mock import MagicMock

# Force UTF-8 encoding for Windows console compatibility
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add src to path (at beginning to override installed package)
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, src_path)

from hcode.core.agent import HcodeAgent
from hcode.providers.base import ToolCall, CompletionResponse, Usage
from hcode.providers.openai_provider import OpenAIProvider
from hcode.tools.base_tool import ToolResult

async def run_validation():
    print("Starting Native Tool Call Validation...")
    
    # 1. Setup Agent with mocked provider
    print("\n[1] Initializing Agent...")
    agent = HcodeAgent(openai_key="mock-key", autonomous_mode=True, openai_model="gpt-oss-120b")
    
    # Create the Mock Provider
    mock_provider = MagicMock(spec=OpenAIProvider)
    mock_provider.name = "openai"
    mock_provider.model = "gpt-oss-120b"
    mock_provider.count_tokens.side_effect = lambda x: 10 
    mock_provider.get_context_window.return_value = 128000
    mock_provider.supports_function_calling.return_value = True
    
    # Initialize total usage to real object
    mock_provider._total_usage = Usage(0, 0, 0)
    # CRITICAL: Set attributes accessed directly
    mock_provider.max_tokens = 4096 
    
    # Verify mock works
    assert isinstance(mock_provider.count_tokens('test'), int), "count_tokens must return int"

    # Mock responses
    tool_call_response = CompletionResponse(
        content="I will read the file now.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[
            ToolCall(
                id="call_123",
                name="ReadTool",
                arguments={"file_path": "README.md"}
            )
        ]
    )
    
    completion_response = CompletionResponse(
        content="Task completed. I read the file.", 
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="stop",
        tool_calls=[]
    )
    
    async def mock_generate(*args, **kwargs):
        count = mock_provider.call_count
        print(f"    -> Mock generate called (count={count})")
        if count == 0:
            print("    -> Returning Mock Tool Call Response")
            mock_provider.call_count += 1
            return tool_call_response
        else:
            print("    -> Returning Mock Completion Response")
            return completion_response
            
    mock_provider.generate_completion = mock_generate
    mock_provider.call_count = 0
    
    # Replace Provider Selector (Aggressive Mocking)
    print("[1.5] Replacing Provider Selector & Context Manager...")
    mock_selector = MagicMock()
    # Mock ALL possible getter methods
    mock_selector.get_provider.return_value = mock_provider
    mock_selector.get_current_provider.return_value = mock_provider
    mock_selector.select_provider.return_value = mock_provider 
    
    agent.provider_selector = mock_selector
    agent.current_provider = mock_provider 
    
    # Mock Context Manager
    mock_context = MagicMock()
    mock_context.get_recent_messages.return_value = [{"role": "user", "content": "Read the readme file"}]
    mock_context.add_message = MagicMock()
    mock_context.set_system_prompt = MagicMock()
    mock_context.get_history.return_value = []
    
    agent.context_manager = mock_context
    
    # Mock tool execution
    original_execute = agent.tool_manager.execute_tool
    execution_log = []
    
    async def mock_execute_tool(name, **kwargs):
        print(f"    -> [EXECUTION] Executing {name} with {kwargs}")
        execution_log.append((name, kwargs))
        if name == "ReadTool" and kwargs.get("file_path") == "README.md":
            # Just verify existence internally since we are mocking
            if os.path.exists(kwargs["file_path"]):
                return ToolResult(success=True, output="File content: # Mock Readme")
            return ToolResult(success=False, output="File not found")
        return ToolResult(success=True, output="Mock result")

    agent._execute_tool_calls_impl = agent._execute_tool_calls_impl if hasattr(agent, "_execute_tool_calls_impl") else None
    agent.tool_manager.execute_tool = mock_execute_tool

    # 2. Run the task
    print("\n[2] Executing Task...")
    try:
        if not os.path.exists("README.md"):
            with open("README.md", "w") as f:
                f.write("# Mock Readme")
        
        # Disable streaming to match our mock response
        await agent.execute_task("Read the readme file", stream=False)
    except Exception as e:
        print(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()

    # 3. Verify Results
    print("\n[3] Verifying Results...")
    
    # Check lowercase tool name as agent normalizes it
    tool_executed = any(name.lower() == "readtool" and args.get("file_path") == "README.md" for name, args in execution_log)
    
    if tool_executed:
        print("SUCCESS: Native ToolCall was processed and executed!")
    else:
        print("FAILURE: ToolCall was NOT executed.")
        print(f"Execution Log: {execution_log}")
        print(f"Mock Provider Call Count: {mock_provider.call_count}")
        sys.exit(1)

    # 4. Test Validation Failure logic
    print("\n[4] Testing Validation Failure...")
    mock_provider.call_count = 0
    
    invalid_tool_response = CompletionResponse(
        content="I will read but forget path.",
        usage=Usage(10, 10, 20),
        model="gpt-oss-120b",
        finish_reason="tool_calls",
        tool_calls=[
            ToolCall(
                id="call_bad",
                name="ReadTool",
                arguments={} 
            )
        ]
    )
    
    async def mock_generate_invalid(*args, **kwargs):
        if mock_provider.call_count == 0:
            print("    -> Returning INVALID Mock Tool Call Response")
            mock_provider.call_count += 1
            return invalid_tool_response
        else:
            print("    -> Returning Mock Completion Response")
            return completion_response

    mock_provider.generate_completion = mock_generate_invalid
    execution_log.clear() 
    
    try:
        await agent.execute_task("Read something invalid", stream=False)
    except Exception:
        pass 
        
    if len(execution_log) == 0:
         print("SUCCESS: Invalid ToolCall was correctly BLOCKED by validation!")
    else:
         print(f"FAILURE: Invalid ToolCall was EXECUTED: {execution_log}")
         sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_validation())
