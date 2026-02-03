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

@runtime_checkable
class ThinkingProcessorProtocol(Protocol):
    """
    Interface for processing thinking blocks from LLM responses.
    
    Responsible for:
    - Parsing <thinking> blocks from response text
    - Validating thinking content
    - Formatting thinking for display
    """
    
    def parse(self, text: str) -> Tuple[Optional[ThinkingBlock], str]:
        """
        Parse thinking block from response text.
        
        Args:
            text: Raw LLM response text
            
        Returns:
            Tuple of (ThinkingBlock or None, remaining text without thinking)
        """
        ...
    
    def is_valid(self, block: Optional[ThinkingBlock]) -> bool:
        """Check if thinking block has meaningful content."""
        ...
    
    def get_summary(self, block: ThinkingBlock) -> str:
        """Get a summary of the thinking content."""
        ...
    
    def display(self, block: ThinkingBlock) -> None:
        """Display thinking block using appropriate formatting."""
        ...


@runtime_checkable
class ResponseParserProtocol(Protocol):
    """
    Interface for parsing LLM responses into tool calls.
    
    Responsible for:
    - Extracting native API tool calls
    - Parsing JSON tool calls from text
    - Validating tool call structure
    """
    
    def extract_tool_calls(
        self, 
        raw_response: Any, 
        response_text: str, 
        provider_name: str
    ) -> List[ParsedToolCall]:
        """
        Extract tool calls from LLM response.
        
        Handles both native API tool calls and text-based JSON tool calls.
        
        Args:
            raw_response: Raw response object from provider
            response_text: Text content of response
            provider_name: Name of the provider (e.g., "openai", "anthropic")
            
        Returns:
            List of parsed tool calls
        """
        ...
    
    def parse_json_tool_calls(self, text: str) -> List[ParsedToolCall]:
        """
        Parse JSON tool calls from text content.
        
        Args:
            text: Text potentially containing JSON tool calls
            
        Returns:
            List of parsed tool calls
        """
        ...


@runtime_checkable
class ToolExecutorProtocol(Protocol):
    """
    Interface for executing tool calls.
    
    Responsible for:
    - Validating tool arguments
    - Executing tools with retry logic
    - Handling tool errors gracefully
    """
    
    async def execute(
        self, 
        tool_calls: List[ParsedToolCall],
        require_confirmation: bool = False
    ) -> List[Tuple[str, ToolResult, Dict[str, Any]]]:
        """
        Execute a list of tool calls.
        
        Args:
            tool_calls: List of tool calls to execute
            require_confirmation: Whether to require user confirmation
            
        Returns:
            List of (tool_name, result, arguments) tuples
        """
        ...
    
    def normalize_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize tool arguments to handle different parameter names.
        
        Args:
            tool_name: Name of the tool
            arguments: Raw arguments from LLM
            
        Returns:
            Normalized arguments dict
        """
        ...


@runtime_checkable
class CompletionDetectorProtocol(Protocol):
    """
    Interface for detecting task completion.
    
    Responsible for:
    - Determining when a task is complete
    - Detecting pending work
    - Checking for substantive answers
    """
    
    def is_complete(
        self, 
        response_text: str, 
        completed_actions: List[Dict[str, Any]], 
        iteration: int
    ) -> CompletionState:
        """
        Check if the task has been completed.
        
        Args:
            response_text: Model's response text
            completed_actions: List of completed tool actions
            iteration: Current iteration number
            
        Returns:
            CompletionState with completion status and details
        """
        ...
    
    def has_pending_work(self, response_text: str) -> bool:
        """
        Check if there's pending work that model should continue.
        
        Args:
            response_text: Model's response text
            
        Returns:
            True if there appears to be pending work
        """
        ...
    
    def has_substantive_answer(self, response_text: str) -> bool:
        """
        Check if response contains actual answer to user's question.
        
        Args:
            response_text: Model's response text
            
        Returns:
            True if response has substantive content
        """
        ...


@runtime_checkable
class PromptBuilderProtocol(Protocol):
    """
    Interface for building system prompts.
    
    Responsible for:
    - Constructing system prompts with tool documentation
    - Injecting context (task.md, implementation_plan.md)
    - Formatting user tasks
    """
    
    def build_system_prompt(self, provider: Any, query: Optional[str] = None) -> str:
        """
        Build complete system prompt with all context.
        
        Args:
            provider: Current LLM provider
            query: Optional user query for memory context
            
        Returns:
            Complete system prompt string
        """
        ...
    
    def format_user_task(self, task: str) -> str:
        """
        Format user task with output format instructions.
        
        Args:
            task: Raw user task
            
        Returns:
            Formatted task string
        """
        ...


@runtime_checkable
class TodoManagerProtocol(Protocol):
    """
    Interface for managing todo items.
    
    Responsible for:
    - Tracking todo completion state
    - Formatting todos for display
    - Checking for pending todos
    """
    
    def get_completion_state(self) -> Dict[str, int]:
        """
        Get current state of todos.
        
        Returns:
            Dict with 'total' and 'completed' counts
        """
        ...
    
    def format_pending(self) -> str:
        """
        Format list of pending todos for context injection.
        
        Returns:
            Formatted string of pending todos
        """
        ...
    
    def has_pending(self) -> bool:
        """
        Check if there are pending or in-progress todos.
        
        Returns:
            True if there are incomplete todos
        """
        ...
    
    def update_from_action(self, completed_action: Dict[str, Any]) -> bool:
        """
        Update todo list based on completed tool action.
        
        Args:
            completed_action: Dict with 'tool', 'success', 'args', 'iteration'
            
        Returns:
            True if a todo was updated
        """
        ...


@runtime_checkable
class LoopDetectorProtocol(Protocol):
    """
    Interface for detecting stuck loops.
    
    Responsible for:
    - Tracking recent responses
    - Detecting repeated responses
    - Signaling when to break out of loops
    """
    
    def add_response(self, response: str) -> None:
        """
        Track a response for loop detection.
        
        Args:
            response: Response text to track
        """
        ...
    
    def is_stuck(self) -> bool:
        """
        Check if model is stuck in a loop.
        
        Returns:
            True if same response repeated too many times
        """
        ...
    
    def reset(self) -> None:
        """Reset detection state."""
        ...


@runtime_checkable
class ResponseCleanerProtocol(Protocol):
    """
    Interface for cleaning responses before display.

    Responsible for:
    - Removing thinking blocks
    - Removing raw JSON tool calls
    - Cleaning up formatting
    """

    def clean(self, response: str) -> str:
        """
        Clean response for user display.

        Args:
            response: Raw accumulated response

        Returns:
            Cleaned response string
        """
        ...


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
