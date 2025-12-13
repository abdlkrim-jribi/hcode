import asyncio
from unittest.mock import MagicMock, AsyncMock
from hcode.agent.workflow_orchestrator import WorkflowOrchestrator
from hcode.providers import Message

# Mock classes
class MockProvider:
    async def generate_completion(self, messages, stream=False):
        # Return a fake reasoning string that the parser can handle
        return AsyncMock(content="""
[PHASE 1: PERCEPTION]
User wants a test.

[PHASE 2: COMPREHENSION]
Context is unit testing.

[PHASE 3: ANALYSIS]
Decomposition:
1. Run test

[PHASE 4: REASONING]
My hypothesis is that this will work.

[PHASE 5: CHANGE IMPACT]
Files affected: none.

[PHASE 6: DECISION]
I decide to run the test.
Confidence: 0.9

[PHASE 7: PRE-EXECUTION REVIEW]
What will change: nothing.

[PHASE 8: VERIFICATION]
Verify: check output.
""")

class MockAgent:
    def __init__(self):
        self.current_provider = MockProvider()
        self.provider_selector = MagicMock()
        self.provider_selector.select_provider.return_value = self.current_provider
    
    async def execute_task(self, task, stream=True, use_sub_agents=False):
        print(f"Agent executing: {task}")
        return "Task Executed Successfully"

async def test_orchestrator():
    agent = MockAgent()
    orchestrator = WorkflowOrchestrator(agent=agent)
    
    print("--- Testing Planning Phase ---")
    reasoning, plan_path = await orchestrator.execute_planning_phase("Create a hello world file")
    print(f"Reasoning Quality: {reasoning.quality_score()}")
    print(f"Plan Path: {plan_path}")
    
    print("\n--- Testing Execution Phase ---")
    results = await orchestrator.execute_execution_phase(reasoning)
    for res in results:
        print(f"Result: {res}")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())
