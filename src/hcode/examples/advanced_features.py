"""
Advanced features example for Hcode.
Demonstrates sub-agents, tools, interactive features, and safety.
"""

import asyncio
from hcode.core import EnhancedHcodeAgent


async def full_featured_example():
    """Complete example with all features"""

    # Initialize enhanced agent
    agent = EnhancedHcodeAgent(
        anthropic_key="your-anthropic-key",
        openai_key="your-openai-key"
    )

    # 1. Explore codebase
    print("=== Exploring Codebase ===")
    exploration = await agent.explore_codebase(
        "Find all API endpoints",
        thoroughness="medium"
    )
    print(exploration)

    # 2. Ask user questions
    print("\n=== Interactive Question ===")
    answers = await agent.ask_user([{
        "question": "Which authentication method should we use?",
        "header": "Auth Method",
        "options": [
            {"label": "JWT", "description": "JSON Web Tokens"},
            {"label": "OAuth2", "description": "OAuth 2.0 flow"},
            {"label": "API Key", "description": "Simple API keys"}
        ],
        "multiSelect": False
    }])
    print(f"User selected: {answers}")

    # 3. Create implementation plan
    print("\n=== Creating Plan ===")
    plan = await agent.plan_implementation(
        "Add rate limiting middleware"
    )
    print(plan)

    # 4. Update todos
    print("\n=== Updating Todos ===")
    await agent.update_todos([
        {
            "content": "Implement rate limiter",
            "status": "in_progress",
            "activeForm": "Implementing rate limiter"
        },
        {
            "content": "Add tests",
            "status": "pending",
            "activeForm": "Adding tests"
        },
        {
            "content": "Update documentation",
            "status": "pending",
            "activeForm": "Updating documentation"
        }
    ])

    # 5. Implement with safety
    print("\n=== Safe Implementation ===")
    tx_id = agent.safety_guard.start_transaction("Rate limiter implementation")

    try:
        result = await agent.implement_with_plan(
            "Implement rate limiting with Redis backend"
        )
        print(result)

        # Commit if successful
        agent.safety_guard.commit_transaction()
        print("✓ Changes committed")

    except Exception as e:
        # Rollback on error
        agent.safety_guard.rollback_transaction()
        print(f"✗ Changes rolled back: {e}")

    # 6. Web search
    print("\n=== Web Search ===")
    search_results = await agent.web_search(
        "Python rate limiting best practices 2024"
    )
    print(search_results[:200])

    # 7. Display stats
    print("\n=== Session Statistics ===")
    stats = agent.get_session_stats()
    print(f"Provider: {stats['provider']}")
    print(f"Total tokens: {stats['total_tokens']:,}")
    print(f"Total cost: ${stats['total_cost']:.4f}")
    print(f"Messages: {stats['message_count']}")


async def parallel_agents_example():
    """Example of running multiple agents in parallel"""
    from hcode.agents import AgentOrchestrator

    agent = EnhancedHcodeAgent(
        anthropic_key="your-key",
        openai_key="your-key"
    )

    orchestrator = AgentOrchestrator(agent.provider_selector)

    # Run multiple agents in parallel
    tasks = [
        {"type": "explore", "query": "Find all database models"},
        {"type": "explore", "query": "Find all API routes"},
        {"type": "explore", "query": "Find all test files"}
    ]

    results = await orchestrator.execute_parallel(tasks)

    for i, result in enumerate(results):
        print(f"\n=== Task {i+1} Results ===")
        print(result.output)


async def safety_features_example():
    """Example demonstrating safety features"""
    agent = EnhancedHcodeAgent(anthropic_key="your-key")

    # Create checkpoint
    checkpoint_id = agent.safety_guard.create_checkpoint("Before refactoring")
    print(f"Created checkpoint: {checkpoint_id}")

    # List backups
    backups = agent.safety_guard.list_backups()
    print(f"Total backups: {len(backups)}")

    # Rollback to checkpoint
    agent.safety_guard.rollback_to_checkpoint(checkpoint_id)
    print("Rolled back to checkpoint")

    # Use dry-run mode
    agent.safety_guard.enable_dry_run()
    result = await agent.execute_task("Refactor authentication module")
    print(f"Dry run result (no changes made): {result}")


if __name__ == "__main__":
    # Run the full example
    asyncio.run(full_featured_example())

    # Or run parallel agents
    # asyncio.run(parallel_agents_example())

    # Or test safety features
    # asyncio.run(safety_features_example())
