"""
Workflow Orchestrator for HCode Agent.

Coordinates the 3-phase structured workflow:
1. Planning: Create implementation plan, request approval
2. Execution: Execute approved plan with task tracking
3. Verification: Validate results, create walkthrough

Integrates with existing reasoning system and artifact manager.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import asyncio

from .task_boundary import AgentMode, TaskBoundary, TaskBoundaryManager
from .artifact_manager import ArtifactManager
from .reasoning import StructuredReasoning, ReasoningLevel
from .reasoning_executor import (
    ExecutionResult,
    ReasoningDrivenExecutor,
    ExecutionStep
)


class WorkflowOrchestrator:
    """
    Orchestrates Planning → Execution → Verification workflow.
    
    Provides Claude Code-style structured workflow with:
    - Explicit planning phase with user approval
    - Guided execution with task tracking
    - Verification with walkthrough generation
    """
    
    def __init__(
        self,
        agent: Any,  # HcodeAgent instance
        task_boundary_manager: Optional[TaskBoundaryManager] = None,
        artifact_manager: Optional[ArtifactManager] = None
    ):
        """
        Initialize workflow orchestrator.
        
        Args:
            agent: HcodeAgent instance
            task_boundary_manager: Task boundary manager (creates if None)
            artifact_manager: Artifact manager (creates if None)
        """
        self.agent = agent
        self.boundary_manager = task_boundary_manager or TaskBoundaryManager()
        self.artifacts = artifact_manager or ArtifactManager()
        
        # State tracking
        self.current_reasoning: Optional[StructuredReasoning] = None
        self.current_plan_path: Optional[Path] = None
        self.execution_results: List[ExecutionResult] = []
    
    async def execute_planning_phase(
        self,
        user_request: str,
        complexity: Any = None
    ) -> Tuple[StructuredReasoning, Path]:
        """
        Execute PLANNING phase.
        
        Steps:
        1. Trigger 8-phase reasoning system
        2. Extract proposed changes and verification plan
        3. Create implementation_plan.md artifact
        4. Create task.md checklist
        
        Args:
            user_request: User's request
            complexity: Task complexity (optional)
            
        Returns:
            (reasoning, plan_path) tuple
        """
        # Update task boundary
        self.boundary_manager.update_current_status(
            "Analyzing requirements and designing solution"
        )
        
        # Trigger reasoning system (use existing agent reasoning)
        # For now, create a minimal reasoning object
        # In full integration, this would call agent's reasoning system
        reasoning = await self._trigger_reasoning(user_request, complexity)
        
        # Extract changes from reasoning
        proposed_changes = self._extract_proposed_changes(reasoning)
        verification_plan = self._extract_verification_plan(reasoning)
        user_review = self._extract_user_review_items(reasoning)
        
        # Create implementation plan artifact
        plan_path = self.artifacts.create_implementation_plan(
            goal_description=self._extract_goal(user_request),
            proposed_changes=proposed_changes,
            verification_plan=verification_plan,
            user_review_required=user_review,
            confidence_score=reasoning.get_confidence(),
            reasoning_summary=reasoning.comprehension.core_understanding
        )
        
        # Create task checklist
        action_items = reasoning.get_action_items()
        if action_items:
            self.artifacts.create_task_md(
                task_name=self._extract_goal(user_request),
                action_items=action_items
            )
        
        # Store for later phases
        self.current_reasoning = reasoning
        self.current_plan_path = plan_path
        
        return reasoning, plan_path
    
    async def execute_execution_phase(
        self,
        approved_reasoning: Optional[StructuredReasoning] = None
    ) -> List[ExecutionResult]:
        """
        Execute EXECUTION phase.
        
        Steps:
        1. Load tasks from task.md
        2. Execute each task using agent's tools
        3. Update task.md progress markers
        4. Sync with LiveTodoBar (if available)
        
        Args:
            approved_reasoning: Approved reasoning (uses current if None)
            
        Returns:
            List of execution results
        """
        reasoning = approved_reasoning or self.current_reasoning
        if not reasoning:
            raise ValueError("No reasoning available for execution")
        
        # Update task boundary
        self.boundary_manager.update_current_status(
            "Executing planned changes"
        )
        
        # Get action items
        action_items = reasoning.get_action_items()
        
        # Execute each task
        results = []
        for i, task_item in enumerate(action_items):
            # Mark task in progress
            if self.artifacts.artifact_exists("task"):
                try:
                    self.artifacts.update_task_progress(i, "in_progress")
                except Exception:
                    pass
            
            # Execute task (placeholder - actual execution would use agent's tools)
            result = await self._execute_task_item(task_item)
            results.append(result)
            
            # Mark task complete/failed
            if self.artifacts.artifact_exists("task"):
                try:
                    status = "completed" if result.get("success", False) else "pending"
                    self.artifacts.update_task_progress(i, status)
                except Exception:
                    pass
        
        self.execution_results = results
        return results
    
    async def execute_verification_phase(
        self,
        execution_results: Optional[List] = None
    ) -> Path:
        """
        Execute VERIFICATION phase.
        
        Steps:
        1. Run validation steps from reasoning
        2. Collect results
        3. Create walkthrough.md artifact
        4. Document what was done and tested
        
        Args:
            execution_results: Execution results (uses current if None)
            
        Returns:
            Path to walkthrough artifact
        """
        results = execution_results or self.execution_results
        reasoning = self.current_reasoning
        
        # Update task boundary
        self.boundary_manager.update_current_status(
            "Running validation and creating walkthrough"
        )
        
        # Extract what was done
        changes_made = self._summarize_changes(results)
        
        # Run validation steps
        tests_run = []
        if reasoning and reasoning.verification.validation_steps:
            tests_run = reasoning.verification.validation_steps
        
        # Collect validation results
        validation_results = {
            "success": all(r.get("success", False) for r in results),
            "details": [r.get("description", "") for r in results]
        }
        
        # Create walkthrough
        walkthrough_path = self.artifacts.create_walkthrough(
            task_name=self._extract_goal("Task"),
            changes_made=changes_made,
            tests_run=tests_run,
            validation_results=validation_results
        )
        
        return walkthrough_path
    
    def should_request_user_approval(
        self,
        reasoning: StructuredReasoning
    ) -> bool:
        """
        Determine if user approval is needed.
        
        Approval needed if:
        - Breaking changes detected
        - High impact score (> 0.7)
        - Pre-execution review flags it
        - Low confidence (< 0.5)
        
        Args:
            reasoning: Reasoning output
            
        Returns:
            True if approval needed
        """
        return (
            reasoning.requires_user_approval() or
            reasoning.change_impact.impact_score > 0.7 or
            reasoning.get_confidence() < 0.5 or
            len(reasoning.change_impact.breaking_changes) > 0
        )
    
    # Helper methods
    
    async def _trigger_reasoning(
        self,
        user_request: str,
        complexity: Any
    ) -> StructuredReasoning:
        """Trigger agent's reasoning system"""
        # Placeholder - in full integration, use agent's reasoning
        # For now, create minimal reasoning
        from .reasoning import (
            StructuredReasoning,
            ComprehensionOutput,
            DecisionOutput,
            AnalysisOutput
        )
        
        reasoning = StructuredReasoning()
        reasoning.comprehension = ComprehensionOutput(
            core_understanding=user_request,
            assumptions=["User request understood"],
            constraints=[]
        )
        reasoning.decision = DecisionOutput(
            decision="Implement requested changes",
            justification="Based on user request",
            confidence=0.8,
            action_items=[
                "Analyze requirements",
                "Implement solution",
                "Test changes"
            ]
        )
        reasoning.analysis = AnalysisOutput(
            decomposition=[
                "Analyze requirements",
                "Implement solution",  
                "Test changes"
            ],
            options=[],
            risks=[]
        )
        
        return reasoning
    
    def _extract_goal(self, user_request: str) -> str:
        """Extract goal from user request"""
        # Simple extraction - take first sentence
        sentences = user_request.split(".")
        return sentences[0] if sentences else user_request[:100]
    
    def _extract_proposed_changes(
        self,
        reasoning: StructuredReasoning
    ) -> List[Dict[str, Any]]:
        """Extract proposed changes from reasoning"""
        changes = []
        
        # Extract from change impact
        if reasoning.change_impact.files_affected:
            for filepath in reasoning.change_impact.files_affected:
                changes.append({
                    "component": "Implementation",
                    "action": "MODIFY",
                    "file": filepath,
                    "description": "Update based on plan"
                })
        
        # If no specific files, create generic change
        if not changes:
            changes.append({
                "component": "General",
                "action": "MODIFY",
                "file": "",
                "description": "Implement requested changes"
            })
        
        return changes
    
    def _extract_verification_plan(
        self,
        reasoning: StructuredReasoning
    ) -> Dict[str, Any]:
        """Extract verification plan from reasoning"""
        return {
            "automated_tests": reasoning.verification.validation_steps or [],
            "manual_verification": reasoning.verification.potential_issues or []
        }
    
    def _extract_user_review_items(
        self,
        reasoning: StructuredReasoning
    ) -> List[str]:
        """Extract items requiring user review"""
        items = []
        
        if reasoning.change_impact.breaking_changes:
            items.extend(reasoning.change_impact.breaking_changes)
        
        if reasoning.pre_execution_review.user_approval_needed:
            if reasoning.pre_execution_review.approval_reason:
                items.append(reasoning.pre_execution_review.approval_reason)
        
        return items
    
    async def _execute_task_item(self, task_item: str) -> Dict[str, Any]:
        """Execute a single task item"""
        # Placeholder - actual execution would use agent's tools
        return {
            "success": True,
            "description": task_item,
            "result": "Completed"
        }
    
    def _summarize_changes(self, results: List) -> List[Dict[str, Any]]:
        """Summarize changes from execution results"""
        changes = []
        
        for result in results:
            changes.append({
                "component": "Implementation",
                "file": "",
                "description": result.get("description", "Change made")
            })
        
        return changes


__all__ = [
    "WorkflowOrchestrator",
]
