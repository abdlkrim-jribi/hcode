"""
Protocol interfaces for the Hcode agent core components.

These protocols define abstract interfaces that enable:
- Dependency injection for testability
- Extension points for customization
- Loose coupling between components

Following the Interface Segregation Principle (ISP), each protocol
is focused on a single role/responsibility.
"""

from typing import Protocol, List, Dict, Any, Optional, Tuple, runtime_checkable
from dataclasses import dataclass, field


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ToolResult:
    """Result from executing a tool."""
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ThinkingBlock:
    """Parsed thinking block from LLM response."""
    raw_content: str
    phase: Optional[str] = None
    summary: Optional[str] = None
    is_valid: bool = False


@dataclass
class ParsedToolCall:
    """Parsed tool call from LLM response."""
    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None
    source: str = "text"  # "native" or "text"


@dataclass 
class CompletionState:
    """State information for task completion detection."""
    is_complete: bool
    reason: Optional[str] = None
    has_pending_work: bool = False
    todos_completed: int = 0
    todos_total: int = 0


# ============================================================================
# Protocol Interfaces
# ============================================================================





# ============================================================================
# Phase Management Protocols (PEV Workflow)
# ============================================================================

@dataclass
class AgentContext:
    """Context object passed through phases."""
    task: str
    session_id: str
    working_dir: str
    iteration: int
    modified_files: List[str] = field(default_factory=list)
    completed_actions: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)  # artifact_name -> file_path
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens_used: Dict[str, int] = field(default_factory=dict)  # phase_name -> token_count
    token_budget: int = 500000  # 500K tokens per task


@dataclass
class PhaseResult:
    """Result from executing a phase."""
    phase_name: str
    success: bool
    output: str
    artifacts_created: List[str] = field(default_factory=list)
    can_transition: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PhaseHandlerProtocol(Protocol):
    """
    Interface for PEV phase handlers.

    Each phase (Planning, Execution, Verification) implements this protocol.
    Provides uniform interface for phase execution and transition logic.
    """

    phase_name: str

    async def handle(
        self,
        context: AgentContext,
        loop_controller: Any,  # AgentLoopController
    ) -> PhaseResult:
        """
        Execute this phase's logic.

        Args:
            context: Current agent context with task, session, etc.
            loop_controller: Loop controller for tracking iterations

        Returns:
            PhaseResult with execution outcome and artifacts
        """
        ...

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """
        Check if ready to transition to next phase.

        Args:
            context: Current agent context

        Returns:
            True if phase is complete and can move to next
        """
        ...

    def get_required_artifacts(self) -> List[str]:
        """
        Get list of artifacts (files) this phase should produce.

        Returns:
            List of artifact names (e.g., ["task.md", "implementation_plan.md"])
        """
        ...

    def validate_artifacts(self, context: AgentContext) -> Tuple[bool, Optional[str]]:
        """
        Validate that required artifacts were created.

        Args:
            context: Current agent context with artifacts

        Returns:
            Tuple of (valid, error_message)
        """
        ...


@runtime_checkable
class PhaseManagerProtocol(Protocol):
    """
    Interface for managing PEV workflow phases.

    Responsible for:
    - Tracking current phase
    - Delegating to appropriate phase handler
    - Managing phase transitions
    - Enforcing PEV workflow
    """

    def get_current_phase(self) -> str:
        """
        Get name of current phase.

        Returns:
            Phase name: "planning", "execution", or "verification"
        """
        ...

    async def execute_current_phase(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute the current phase.

        Args:
            context: Current agent context
            loop_controller: Loop controller for tracking

        Returns:
            PhaseResult from current phase handler
        """
        ...

    def transition_to_next_phase(self, context: AgentContext) -> bool:
        """
        Attempt to transition to next phase.

        Args:
            context: Current agent context

        Returns:
            True if transition successful
        """
        ...

    def can_complete(self, context: AgentContext) -> bool:
        """
        Check if all phases are complete.

        Args:
            context: Current agent context

        Returns:
            True if workflow is complete
        """
        ...


@runtime_checkable
class TaskClassifierProtocol(Protocol):
    """
    Interface for task classification.

    Responsible for:
    - Classifying user tasks by type
    - Determining task complexity
    - Providing confidence scores
    """

    def classify(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Classify the task type.

        Args:
            task: User's task description
            context: Optional context for classification

        Returns:
            Task type: "exploration", "implementation", "debugging",
                      "refactoring", "testing", "documentation"
        """
        ...

    def get_complexity(self, task: str) -> str:
        """
        Determine task complexity.

        Args:
            task: User's task description

        Returns:
            Complexity: "simple", "moderate", "complex"
        """
        ...

    def get_confidence(self) -> float:
        """
        Get confidence score for last classification.

        Returns:
            Confidence score between 0.0 and 1.0
        """
        ...

    def is_read_only(self, task: str) -> bool:
        """
        Check if task is read-only (exploration, explanation).

        Args:
            task: User's task description

        Returns:
            True if task doesn't require file modifications
        """
        ...


@runtime_checkable
class ArtifactManagerProtocol(Protocol):
    """
    Interface for managing phase artifacts.

    Responsible for:
    - Creating phase artifacts (task.md, implementation_plan.md, walkthrough.md)
    - Validating artifact existence and content
    - Loading artifacts for phase transitions
    """

    def create_artifact(
        self,
        artifact_name: str,
        content: str,
        context: AgentContext,
    ) -> str:
        """
        Create a phase artifact file.

        Args:
            artifact_name: Name of artifact (e.g., "task.md")
            content: Content to write
            context: Current agent context

        Returns:
            Full path to created artifact
        """
        ...

    def load_artifact(
        self,
        artifact_name: str,
        context: AgentContext,
    ) -> Optional[str]:
        """
        Load artifact content.

        Args:
            artifact_name: Name of artifact to load
            context: Current agent context

        Returns:
            Artifact content or None if doesn't exist
        """
        ...

    def artifact_exists(
        self,
        artifact_name: str,
        context: AgentContext,
    ) -> bool:
        """
        Check if artifact exists.

        Args:
            artifact_name: Name of artifact
            context: Current agent context

        Returns:
            True if artifact file exists
        """
        ...

    def validate_artifact_content(
        self,
        artifact_name: str,
        content: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate artifact has required content.

        Args:
            artifact_name: Name of artifact
            content: Artifact content to validate

        Returns:
            Tuple of (valid, error_message)
        """
        ...


@runtime_checkable
class AgentOrchestratorProtocol(Protocol):
    """
    Interface for orchestrating agent execution.

    Responsible for:
    - Coordinating overall agent execution
    - Managing phase workflow
    - Handling execution lifecycle
    - Delegating to appropriate services
    """

    async def execute_task(
        self,
        task: str,
        session_id: str,
        stream_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute a user task through the PEV workflow.

        Args:
            task: User's task description
            session_id: Session identifier
            stream_callback: Optional callback for streaming responses

        Returns:
            Dict with execution results including:
            - success: bool
            - output: str
            - modified_files: List[str]
            - artifacts: Dict[str, str]
        """
        ...

    def initialize_context(self, task: str, session_id: str) -> AgentContext:
        """
        Initialize agent context for new task.

        Args:
            task: User's task
            session_id: Session identifier

        Returns:
            Initialized AgentContext
        """
        ...

    async def execute_phase_iteration(
        self,
        context: AgentContext,
    ) -> PhaseResult:
        """
        Execute one iteration of current phase.

        Args:
            context: Current agent context

        Returns:
            PhaseResult from phase execution
        """
        ...
