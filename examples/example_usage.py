"""
Example usage of Hcode Python API.
Demonstrates how to use Hcode programmatically.
"""

import asyncio
from hcode.core import HcodeAgent
from hcode.providers import ProviderPreferences, TaskComplexity, TaskType


async def main():
    """Main example function"""

    # Example 1: Basic usage with automatic provider selection
    print("=== Example 1: Basic Task Execution ===")

    agent = HcodeAgent(
        anthropic_key="your-anthropic-key",
        openai_key="your-openai-key"
    )

    result = await agent.execute_task(
        "Create a function to calculate fibonacci numbers",
        complexity=TaskComplexity.SIMPLE,
        task_type=TaskType.CODE_GENERATION,
        stream=False
    )

    print(result)

    # Example 2: Using specific provider
    print("\n=== Example 2: Specific Provider ===")

    preferences = ProviderPreferences(
        primary_provider="anthropic",
        cost_optimization="quality"
    )

    agent = HcodeAgent(
        anthropic_key="your-anthropic-key",
        preferences=preferences
    )

    result = await agent.execute_task(
        "Refactor this code for better performance",
        complexity=TaskComplexity.MODERATE,
        stream=False
    )

    print(result)

    # Example 3: Code analysis
    print("\n=== Example 3: Code Analysis ===")

    analysis = await agent.analyze_code("src/main.py")
    print(analysis)

    # Example 4: Planning and implementation
    print("\n=== Example 4: Plan and Implement ===")

    plan = await agent.plan_approach(
        "Build a REST API for user authentication with JWT"
    )

    print("Plan:", plan["plan"])

    implementation = await agent.implement_solution(plan)
    print("Implementation:", implementation)

    # Example 5: Debugging
    print("\n=== Example 5: Debug Issue ===")

    debug_result = await agent.debug_issue(
        "Getting TypeError: 'NoneType' object is not callable in user_service.py line 42"
    )

    print(debug_result)

    # Example 6: Session management
    print("\n=== Example 6: Session Stats ===")

    stats = agent.get_session_stats()
    print("Total cost:", stats["total_cost"])
    print("Messages:", stats["context"]["total_messages"])

    # Example 7: Export session
    agent.export_session("session_backup.json")


if __name__ == "__main__":
    asyncio.run(main())
