"""
Advanced Features Examples for Hcode.
Demonstrates all Hcode-inspired features.
"""

import asyncio
from hcode.core import EnhancedHcodeAgent
from hcode.providers import ProviderPreferences
from hcode.tools import ToolManager


async def example_1_comprehensive_tools():
    """Example 1: Using comprehensive tool system"""
    print("=== Example 1: Comprehensive Tool System ===\n")

    agent = EnhancedHcodeAgent(anthropic_key="your-key", openai_key="your-key")

    # Use Read tool
    print("Reading file...")
    result = await agent.tool_manager.read_file("main.py", offset=1, limit=20)
    print(result.output[:200], "...")

    # Use Grep tool to search code
    print("\nSearching for 'async def'...")
    result = await agent.tool_manager.search_files(
        pattern="async def", glob="**/*.py", output_mode="content"
    )
    print(result.output[:200], "...")

    # Use Glob tool to find files
    print("\nFinding Python files...")
    result = await agent.tool_manager.find_files("**/*.py")
    print(result.output[:200], "...")


async def example_2_sub_agents():
    """Example 2: Using specialized sub-agents"""
    print("\n=== Example 2: Specialized Sub-Agents ===\n")

    agent = EnhancedHcodeAgent(anthropic_key="your-key", openai_key="your-key")

    # Explore codebase
    print("Exploring codebase...")
    exploration = await agent.explore_codebase(
        "Find all API endpoints in the project", thoroughness="medium"
    )
    print(exploration[:200], "...")

    # Create implementation plan
    print("\nCreating plan...")
    plan = await agent.plan_implementation("Add rate limiting to API endpoints", explore_first=True)
    print(plan[:200], "...")

    # Full implementation flow
    print("\nFull implementation...")
    result = await agent.implement_with_plan("Add logging to all database queries")
    print(result[:200], "...")


async def example_3_interactive_features():
    """Example 3: Interactive features"""
    print("\n=== Example 3: Interactive Features ===\n")

    agent = EnhancedHcodeAgent(anthropic_key="your-key", openai_key="your-key")

    # Ask user questions
    print("Asking user questions...")
    questions = [
        {
            "question": "Which database should we use?",
            "header": "Database",
            "options": [
                {"label": "PostgreSQL", "description": "Robust relational database"},
                {"label": "MongoDB", "description": "Flexible document database"},
                {"label": "Redis", "description": "Fast in-memory data store"},
            ],
            "multi_select": False,
        }
    ]

    answers = await agent.ask_user(questions)
    print(f"User selected: {answers}")

    # Update todos
    print("\nUpdating todos...")
    todos = [
        {
            "content": "Set up database",
            "status": "in_progress",
            "activeForm": "Setting up database",
        },
        {"content": "Create models", "status": "pending", "activeForm": "Creating models"},
        {"content": "Write migrations", "status": "pending", "activeForm": "Writing migrations"},
    ]
    await agent.update_todos(todos)


async def example_4_web_capabilities():
    """Example 4: Web capabilities"""
    print("\n=== Example 4: Web Capabilities ===\n")

    agent = EnhancedHcodeAgent(anthropic_key="your-key", openai_key="your-key")

    # Web search
    print("Searching web...")
    results = await agent.web_search("Python async best practices 2024", num_results=5)
    print(results[:200], "...")

    # Fetch web content
    print("\nFetching web page...")
    content = await agent.web_fetch(
        "https://docs.python.org/3/library/asyncio.html", "Summarize key asyncio concepts"
    )
    print(content[:200], "...")


async def example_5_notebook_support():
    """Example 5: Jupyter notebook support"""
    print("\n=== Example 5: Jupyter Notebook Support ===\n")

    tool_manager = ToolManager()

    # Read notebook
    print("Reading notebook...")
    result = await tool_manager.execute_tool(
        "notebookreadtool", notebook_path="analysis.ipynb", include_outputs=True
    )
    if result.success:
        print(result.output[:200], "...")

    # Edit notebook cell
    print("\nEditing notebook cell...")
    result = await tool_manager.execute_tool(
        "notebookedittool",
        notebook_path="analysis.ipynb",
        cell_id="cell-1",
        new_source="import pandas as pd\nimport numpy as np",
        edit_mode="replace",
    )
    print(result.output)


async def example_6_slash_commands():
    """Example 6: Slash commands and skills"""
    print("\n=== Example 6: Slash Commands & Skills ===\n")

    # First, create custom commands in .hcode/commands/

    tool_manager = ToolManager()

    # Execute slash command
    print("Executing slash command...")
    result = await tool_manager.execute_tool("slashcommandtool", command="/review-pr 123")
    if result.success:
        print("Command expanded:", result.output[:100], "...")

    # Invoke skill
    print("\nInvoking skill...")
    result = await tool_manager.execute_tool(
        "skilltool", skill="code-review", context={"file": "main.py"}
    )
    if result.success:
        print("Skill executed:", result.output[:100], "...")


async def example_7_parallel_execution():
    """Example 7: Parallel agent execution"""
    print("\n=== Example 7: Parallel Execution ===\n")

    agent = EnhancedHcodeAgent(anthropic_key="your-key", openai_key="your-key")

    # Execute multiple sub-agents in parallel
    from hcode.agents import AgentType

    results = await agent.agent_orchestrator.execute_with_agents(
        task="Analyze project for improvements",
        agent_types=[AgentType.EXPLORE, AgentType.PLAN],
        parallel=True,  # Parallel execution
    )

    for result in results:
        print(f"{result.agent_type}: {result.output[:100]}...")


async def example_8_full_workflow():
    """Example 8: Complete workflow with all features"""
    print("\n=== Example 8: Complete Workflow ===\n")

    agent = EnhancedHcodeAgent(anthropic_key="your-key", openai_key="your-key")

    # Step 1: Ask user for requirements
    questions = [
        {
            "question": "What type of feature do you want to add?",
            "header": "Feature Type",
            "options": [
                {"label": "API Endpoint", "description": "Add new REST API endpoint"},
                {"label": "Database Model", "description": "Add new database model"},
                {"label": "UI Component", "description": "Add new UI component"},
            ],
            "multi_select": False,
        }
    ]

    answers = await agent.ask_user(questions)
    feature_type = answers.get("Feature Type", "API Endpoint")

    # Step 2: Explore existing code
    exploration = await agent.explore_codebase(
        f"Find existing {feature_type} implementations", thoroughness="medium"
    )

    # Step 3: Create plan
    plan = await agent.plan_implementation(
        f"Add new {feature_type} following project conventions",
        explore_first=False,  # Already explored
    )

    # Step 4: Show todos
    todos = [
        {"content": "Explore codebase", "status": "completed", "activeForm": "Exploring codebase"},
        {
            "content": "Create implementation plan",
            "status": "completed",
            "activeForm": "Creating implementation plan",
        },
        {
            "content": "Implement feature",
            "status": "in_progress",
            "activeForm": "Implementing feature",
        },
        {"content": "Write tests", "status": "pending", "activeForm": "Writing tests"},
        {
            "content": "Update documentation",
            "status": "pending",
            "activeForm": "Updating documentation",
        },
    ]
    await agent.update_todos(todos)

    # Step 5: Implement with safety
    tx_id = agent.safety_guard.start_transaction(f"Add {feature_type}")

    try:
        result = await agent.implement_with_plan(f"Implement {feature_type} according to plan")
        agent.safety_guard.commit_transaction()
        print("Implementation completed successfully!")

    except Exception as e:
        agent.safety_guard.rollback_transaction()
        print(f"Implementation failed, rolled back: {e}")

    # Step 6: Show session stats
    stats = agent.get_session_stats()
    print(f"\nSession Stats:")
    print(f"  Cost: ${stats['total_cost']:.4f}")
    print(f"  Provider: {stats['provider']}")
    print(f"  Tool usage: {stats['tool_usage']}")


async def main():
    """Run all examples"""
    # Uncomment the examples you want to run

    # await example_1_comprehensive_tools()
    # await example_2_sub_agents()
    # await example_3_interactive_features()
    # await example_4_web_capabilities()
    # await example_5_notebook_support()
    # await example_6_slash_commands()
    # await example_7_parallel_execution()
    await example_8_full_workflow()


if __name__ == "__main__":
    asyncio.run(main())
