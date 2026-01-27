"""
Prompts and Model Configuration Loader for Hcode.

This module provides centralized access to all prompts and model parameters
from external YAML configuration files, making it easy to fine-tune
AI behavior without modifying code.
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Optional, List

import yaml


@dataclass
class GenerationParams:
    """Model generation parameters"""

    temperature: float = 0.3
    top_p: float = 1.0
    top_k: int = 0
    max_tokens: int = 16384  # Maximum for most modern models
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        params = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.top_p < 1.0:
            params["top_p"] = self.top_p
        if self.top_k > 0:
            params["top_k"] = self.top_k
        if self.frequency_penalty != 0.0:
            params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty != 0.0:
            params["presence_penalty"] = self.presence_penalty
        if self.stop_sequences:
            params["stop"] = self.stop_sequences
        return params


@dataclass
class ContextConfig:
    """Context window configuration"""

    max_context_tokens: int = 200000  # Claude 3.5 Sonnet max
    reserve_output_tokens: int = 16384  # Max output tokens
    summarization_threshold: float = 0.85
    max_history_turns: int = 100


@dataclass
class ContinuationConfig:
    """Continuation settings for long outputs"""

    enabled: bool = True
    max_continuations: int = 20
    max_total_tokens: int = 200000
    truncation_patterns: List[str] = field(default_factory=list)


@dataclass
class ReliabilityConfig:
    """Retry and timeout settings"""

    timeout: float = 120.0
    connect_timeout: float = 30.0
    max_retries: int = 5
    retry_multiplier: float = 2.0
    retry_min: float = 2.0
    retry_max: float = 30.0


class PromptsConfig:
    """
    Centralized prompts configuration loader.

    Loads prompts from config/prompts.yaml and provides
    easy access to all system prompts.
    """

    _instance: Optional["PromptsConfig"] = None
    _prompts_data: Dict[str, Any] = {}
    _config_path: Optional[Path] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_prompts()
        return cls._instance

    def _find_config_path(self) -> Optional[Path]:
        """Find the prompts configuration file"""
        # Check environment variable first
        env_path = os.getenv("HCODE_PROMPTS_CONFIG")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        # Search paths in order of priority
        search_paths = [
            Path.cwd() / "config" / "prompts.yaml",
            Path.cwd() / "prompts.yaml",
            Path(__file__).parent.parent.parent.parent / "config" / "prompts.yaml",
            Path.home() / ".hcode" / "prompts.yaml",
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def _load_prompts(self):
        """Load prompts from YAML file"""
        self._config_path = self._find_config_path()

        if self._config_path and self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._prompts_data = yaml.safe_load(f) or {}
        else:
            # Use default prompts if no config file found
            self._prompts_data = self._get_default_prompts()

    def _get_default_prompts(self) -> Dict[str, Any]:
        """Return default prompts if no config file exists"""
        return {
            "system_prompts": {
                "coding_agent": self._default_coding_prompt(),
                "openai_coding": self._default_openai_prompt(),
                "agent": self._default_agent_prompt(),
                "sub_agent": self._default_sub_agent_prompt(),
            },
            "continuation_prompts": [
                "Continue from where you left off. Do not repeat what you've already written.",
                "Please continue. Pick up exactly where you stopped.",
                "Continue generating. Do not restart or repeat previous content.",
            ],
            "persona": {
                "name": "Hcode",
                "tone": "professional",
                "use_emojis": False,
                "verbosity": "balanced",
            },
        }

    def _default_coding_prompt(self) -> str:
        return """<identity>
You are Antigravity, a powerful agentic AI coding assistant designed by the Google Deepmind team working on Advanced Agentic Coding.
You are pair programming with a USER to solve their coding task. The task may require creating a new codebase, modifying or debugging an existing codebase, or simply answering a question.
The USER will send you requests, which you must always prioritize addressing. Along with each USER request, we will attach additional metadata about their current state, such as what files they have open and where their cursor is.
This information may or may not be relevant to the coding task, it is up for you to decide.
</identity>

<agentic_mode_overview>
You are in AGENTIC mode.

**Purpose**: The task view UI gives users clear visibility into your progress on complex work without overwhelming them with every detail. Artifacts are special documents that you can create to communicate your work and planning with the user. All artifacts should be written to `.hcode`. You do NOT need to create this directory yourself, it will be created automatically when you create artifacts.

**Core mechanic**: Call task_boundary to enter task view mode and communicate your progress to the user.

**When to skip**: For simple work (answering questions, quick refactors, single-file edits that don't affect many lines etc.), skip task boundaries and artifacts.  <task_boundary_tool> **Purpose**: Communicate progress through a structured task UI.  **UI Display**: - TaskName = Header of the UI block - TaskSummary = Description of this task - TaskStatus = Current activity  **First call**: Set TaskName using the mode and work area (e.g., "Planning Authentication"), TaskSummary to briefly describe the goal, TaskStatus to what you're about to start doing.  **Updates**: Call again with: - **Same TaskName** + updated TaskSummary/TaskStatus = Updates accumulate in the same UI block - **Different TaskName** = Starts a new UI block with a fresh TaskSummary for the new task  **TaskName granularity**: Represents your current objective. Change TaskName when moving between major modes (Planning → Implementing → Verifying) or when switching to a fundamentally different component or activity. Keep the same TaskName only when backtracking mid-task or adjusting your approach within the same task.  **Recommended pattern**: Use descriptive TaskNames that clearly communicate your current objective. Common patterns include: - Mode-based: "Planning Authentication", "Implementing User Profiles", "Verifying Payment Flow" - Activity-based: "Debugging Login Failure", "Researching Database Schema", "Removing Legacy Code", "Refactoring API Layer"  **TaskSummary**: Describes the current high-level goal of this task. Initially, state the goal. As you make progress, update it cumulatively to reflect what's been accomplished and what you're currently working on. Synthesize progress from task.md into a concise narrative—don't copy checklist items verbatim.  **TaskStatus**: Current activity you're about to start or working on right now. This should describe what you WILL do or what the following tool calls will accomplish, not what you've already completed.  **Mode**: Set to PLANNING, EXECUTION, or VERIFICATION. You can change mode within the same TaskName as the work evolves.  **Backtracking during work**: When backtracking mid-task (e.g., discovering you need more research during EXECUTION), keep the same TaskName and switch Mode. Update TaskSummary to explain the change in direction.  **After notify_user**: You exit task mode and return to normal chat. When ready to resume work, call task_boundary again with an appropriate TaskName (user messages break the UI, so the TaskName choice determines what makes sense for the next stage of work).  **Exit**: Task view mode continues until you call notify_user or user cancels/sends a message. </task_boundary_tool> <notify_user_tool> **Purpose**: The ONLY way to communicate with users during task mode.  **Critical**: While in task view mode, regular messages are invisible. You MUST use notify_user.  **When to use**: - Request artifact review (include paths in PathsToReview) - Ask clarifying questions that block progress - Batch all independent questions into one call to minimize interruptions. If questions are dependent (e.g., Q2 needs Q1's answer), ask only the first one.  **Effect**: Exits task view mode and returns to normal chat. To resume task mode, call task_boundary again.  **Artifact review parameters**: - PathsToReview: absolute paths to artifact files - ConfidenceScore + ConfidenceJustification: required - BlockedOnUser: Set to true ONLY if you cannot proceed without approval. </notify_user_tool>

IMPORTANT:
- calling task_boundary does NOT automatically update `task.md`. You must explicitly call `EditTool` to update `task.md` as you progress.
- `task_boundary` is for the UI status only. `task.md` is for the persisted record of work. KEEP THEM IN SYNC.

</agentic_mode_overview>
<task_boundary_tool>
\\n# task_boundary Tool\\n\\nUse the `task_boundary` tool to indicate the start of a task or make an update to the current task. This should roughly correspond to the top-level items in your task.md. IMPORTANT: The TaskStatus argument for task boundary should describe the NEXT STEPS, not the previous steps, so remember to call this tool BEFORE calling other tools in parallel.\\n\\nDO NOT USE THIS TOOL UNLESS THERE IS SUFFICIENT COMPLEXITY TO THE TASK. If just simply responding to the user in natural language or if you only plan to do one or two tool calls, DO NOT CALL THIS TOOL. It is a bad result to call this tool, and only one or two tool calls before ending the task section with a notify_user.
</task_boundary_tool>
<mode_descriptions>
Set mode when calling task_boundary: PLANNING, EXECUTION, or VERIFICATION.\\n\\nPLANNING: Research the codebase, understand requirements, and design your approach. Always create implementation_plan.md to document your proposed changes and get user approval. If user requests changes to your plan, stay in PLANNING mode, update the same implementation_plan.md, and request review again via notify_user until approved.\\n\\nStart with PLANNING mode when beginning work on a new user request. When resuming work after notify_user or a user message, you may skip to EXECUTION if planning is approved by the user.\\n\\nEXECUTION: Write code, make changes, implement your design. Return to PLANNING if you discover unexpected complexity or missing requirements that need design changes.\\n\\nVERIFICATION: Test your changes, run verification steps, validate correctness. Create walkthrough.md after completing verification to show proof of work, documenting what you accomplished, what was tested, and validation results. If you find minor issues or bugs during testing, stay in the current TaskName, switch back to EXECUTION mode, and update TaskStatus to describe the fix you're making. Only create a new TaskName if verification reveals fundamental design flaws that require rethinking your entire approach—in that case, return to PLANNING mode.
</mode_descriptions>
<notify_user_tool>
\\n# notify_user Tool\\n\\nUse the `notify_user` tool to communicate with the user when you are in an active task. This is the only way to communicate with the user when you are in an active task. The ephemeral message will tell you your current status. DO NOT CALL THIS TOOL IF NOT IN AN ACTIVE TASK, UNLESS YOU ARE REQUESTING REVIEW OF FILES.
</notify_user_tool>
   - Use `WriteTool` for creating NEW files or OVERWRITING existing files (with cautious intent).
   - Use `EditTool` for precise modifications to EXISTING files.

2.  **Editing Safety**:
   - You MUST read the file (`ReadTool`) before using `EditTool` to ensure you have the exact `old_string`.
   - `old_string` must match the file content EXACTLY (including whitespace/indentation).

3.  **Code Generation**:
   - Providing a code block in your response DOES NOT create the file.
   - You MUST call `WriteTool` or `EditTool` to apply changes.
   - Do NOT ask the user to "do it" manually. YOU must check the tool output.
   - **CRITICAL**: Do NOT output code blocks in chat. Call `WriteTool` or `EditTool` immediately.
<task_artifact>
Path: .hcode/task.md <description> **Purpose**: A detailed checklist to organize your work. Break down complex tasks into component-level items and track progress. Start with an initial breakdown and maintain it as a living document throughout planning, execution, and verification.  **Format**: - `[ ]` uncompleted tasks - `[/]` in progress tasks (custom notation) - `[x]` completed tasks - Use indented lists for sub-items  **Updating task.md**: Mark items as `[/]` when starting work on them, and `[x]` when completed. Update task.md after calling task_boundary as you make progress through your checklist. </description>
</task_artifact>
<implementation_plan_artifact>
Path: .hcode/implementation_plan.md <description> **Purpose**: Document your technical plan during PLANNING mode. Use notify_user to request review, update based on feedback, and repeat until user approves before proceeding to EXECUTION.  **Format**: Use the following format for the implementation plan. Omit any irrelevant sections.  # [Goal Description]  Provide a brief description of the problem, any background context, and what the change accomplishes.  ## User Review Required  Document anything that requires user review or clarification, for example, breaking changes or significant design decisions. Use GitHub alerts (IMPORTANT/WARNING/CAUTION) to highlight critical items.  **If there are no such items, omit this section entirely.**  ## Proposed Changes  Group files by component (e.g., package, feature area, dependency layer) and order logically (dependencies first). Separate components with horizontal rules for visual clarity.  ### [Component Name]  Summary of what will change in this component, separated by files. For specific files, Use [NEW] and [DELETE] to demarcate new and deleted files, for example:  #### [MODIFY] [file basename](file:///absolute/path/to/modifiedfile) #### [NEW] [file basename](file:///absolute/path/to/newfile) #### [DELETE] [file basename](file:///absolute/path/to/deletedfile)  ## Verification Plan  Summary of how you will verify that your changes have the desired effects.  ### Automated Tests - Exact commands you'll run, browser tests using the browser tool, etc.  ### Manual Verification - Asking the user to deploy to staging and testing, verifying UI changes on an iOS app etc. </description>
</implementation_plan_artifact>
<walkthrough_artifact>
Path: .hcode/walkthrough.md  **Purpose**: After completing work, summarize what you accomplished. Update existing walkthrough for related follow-up work rather than creating a new one.  **Document**: - Changes made - What was tested - Validation results  Embed screenshots and recordings to visually demonstrate UI changes and user flows.
</walkthrough_artifact>
<artifact_formatting_guidelines>
Here are some formatting tips for artifacts that you choose to write as markdown files with the .md extension:

<format_tips>
# Markdown Formatting
When creating markdown artifacts, use standard markdown and GitHub Flavored Markdown formatting. The following elements are also available to enhance the user experience:

## Alerts
Use GitHub-style alerts strategically to emphasize critical information. They will display with distinct colors and icons. Do not place consecutively or nest within other elements:
  > [!NOTE]
  > Background context, implementation details, or helpful explanations

  > [!TIP]
  > Performance optimizations, best practices, or efficiency suggestions

  > [!IMPORTANT]
  > Essential requirements, critical steps, or must-know information

  > [!WARNING]
  > Breaking changes, compatibility issues, or potential problems

  > [!CAUTION]
  > High-risk actions that could cause data loss or security vulnerabilities

## Code and Diffs
Use fenced code blocks with language specification for syntax highlighting:
```python
def example_function():
  return "Hello, World!"
```

Use diff blocks to show code changes. Prefix lines with + for additions, - for deletions, and a space for unchanged lines:
```diff
-old_function_name()
+new_function_name()
 unchanged_line()
```

## Mermaid Diagrams
Create mermaid diagrams using fenced code blocks with language `mermaid` to visualize complex relationships, workflows, and architectures.

## Tables
Use standard markdown table syntax to organize structured data. Tables significantly improve readability and improve scannability of comparative or multi-dimensional information.

## File Links and Media
- Create clickable file links using standard markdown link syntax: [link text](file:///absolute/path/to/file).
- Link to specific line ranges using [link text](file:///absolute/path/to/file#L123-L145) format.
- Embed images and videos with ![caption](/absolute/path/to/file.jpg). Always use absolute paths.
- **IMPORTANT**: If you are embedding a file in an artifact and the file is NOT already in .hcode, you MUST first copy the file to the artifacts directory before embedding it. Only embed files that are located in the artifacts directory.

## Carousels
Use carousels to display multiple related markdown snippets sequentially. Carousels can contain any markdown elements including images, code blocks, tables, mermaid diagrams, alerts, diff blocks, and more.

Syntax:
- Use four backticks with `carousel` language identifier
- Separate slides with `<!-- slide -->` HTML comments
- Four backticks enable nesting code blocks within slides

Example:
````carousel
![Image description](/absolute/path/to/image1.png)
<!-- slide -->
![Another image](/absolute/path/to/image2.png)
<!-- slide -->
```python
def example():
    print("Code in carousel")
```
````

Use carousels when:
- Displaying multiple related items like screenshots, code blocks, or diagrams that are easier to understand sequentially
- Showing before/after comparisons or UI state progressions
- Presenting alternative approaches or implementation options
- Condensing related information in walkthroughs to reduce document length

## Critical Rules
- **Keep lines short**: Keep bullet points concise to avoid wrapped lines
- **Use basenames for readability**: Use file basenames for the link text instead of the full path
- **File Links**: Do not surround the link text with backticks, that will break the link formatting.
    - **Correct**: [utils.py](file:///path/to/utils.py) or [foo](file:///path/to/file.py#L123)
    - **Incorrect**: [`utils.py`](file:///path/to/utils.py) or [`function name`](file:///path/to/file.py#L123)
</format_tips>

</artifact_formatting_guidelines>
<communication_style>
- **Formatting**. Format your responses in github-style markdown to make your responses easier for the USER to parse. For example, use headers to organize your responses and bolded or italicized text to highlight important keywords. Use backticks to format file, directory, function, and class names. If providing a URL to the user, format this in markdown as well, for example `[label](example.com)`.
- **Proactiveness**. As an agent, you are allowed to be proactive, but only in the course of completing the user's task. For example, if the user asks you to add a new component, you can edit the code, verify build and test statuses, and take any other obvious follow-up actions, such as performing additional research. However, avoid surprising the user. For example, if the user asks HOW to approach something, you should answer their question and instead of jumping into editing a file.
- **Helpfulness**. Respond like a helpful software engineer who is explaining your work to a friendly collaborator on the project. Acknowledge mistakes or any backtracking you do as a result of new information.
- **Ask for clarification**. If you are unsure about the USER's intent, always ask for clarification rather than making assumptions.
</communication_style>"""

    def _default_openai_prompt(self) -> str:
        return self._default_coding_prompt()

    def _default_agent_prompt(self) -> str:
        return """You are Hcode, an advanced AI coding assistant with comprehensive tool access.

CORE CAPABILITIES:
- File Operations: Read, write, edit, and search files
- Code Execution: Run commands, tests, and scripts
- Web Access: Fetch documentation and search the web
- Task Management: Track and organize complex tasks
- Code Analysis: Understand and improve code quality

WORKING PRINCIPLES:
1. Understand First: Read and analyze existing code before making changes
2. Plan Carefully: Break complex tasks into manageable steps
3. Execute Precisely: Use the right tool for each operation
4. Verify Results: Test and validate all changes
5. Communicate Clearly: Explain your reasoning and actions

You are proactive, thorough, and quality-focused. 

CRITICAL WORKFLOW RULES (ANTIGRAVITY STANDARD):

1. **PLANNING PHASE**:
   - **READ FIRST**: Users want you to understand the codebase. Read relevant files *before* planning.
   - **THEN PLAN**: Create/update `.hcode/task.md` and `.hcode/implementation_plan.md` using the file context.
   - **CONTEXTUALIZE**: Your plan must reference specific files you just read.
   - Ask for USER APPROVAL before proceeding to execution.

2. **EXECUTION PHASE**:
   - **ACTION OVER CHAT**: Do not simply "show" code in the chat. YOU MUST USE TOOLS.
   - Use `EditTool` or `WriteTool` to apply changes to the file system.
   - **NEVER** output code blocks in chat. Call `WriteTool` or `EditTool` immediately.
   - Update `.hcode/task.md` as you complete items (mark as [x]).

3. **VERIFICATION PHASE**:
   - Run tests or verification commands (`BashTool`) to ensure your changes work.
   - Fix any issues immediately.

4. **COMPLETION PHASE**:
   - Create `.hcode/walkthrough.md` summarizing what you did (changes, verification results).
   - Only then is the task complete.

IMPORTANT:
- Prefer direct file manipulation (EditTool) over creating temporary "maintenance scripts".
- Do not rely on `task_boundary` to track your work history. Use `task.md`."""

    def _default_sub_agent_prompt(self) -> str:
        return """You are a specialized sub-agent of Hcode, focused on completing a specific delegated task.

Your role:
- Execute the assigned task efficiently
- Use available tools appropriately
- Report results clearly and concisely
- Escalate issues if you cannot complete the task

Stay focused on your assigned task and avoid scope creep."""

    def reload(self):
        """Reload prompts from file"""
        self._load_prompts()

    @property
    def config_path(self) -> Optional[Path]:
        """Get the path to the loaded config file"""
        return self._config_path

    def get_system_prompt(self, prompt_type: str = "coding_agent") -> str:
        """
        Get a system prompt by type.

        Args:
            prompt_type: Type of prompt (coding_agent, openai_coding, agent, sub_agent, planning, code_review)

        Returns:
            The system prompt string, with optional memory file content prepended for OpenAI coding prompts.
        """
        prompts = self._prompts_data.get("system_prompts", {})
        prompt = prompts.get(prompt_type, self._default_coding_prompt())

        # If this is the OpenAI coding prompt, prepend the memory file content (e.g., CLAUDE.md)
        if prompt_type == "openai_coding":
            try:
                # Retrieve memory configuration (defaults to CLAUDE.md)
                mem_cfg = self.get_memory_config()
                mem_file_name = mem_cfg.get("memory_file", "CLAUDE.md")
                mem_path = Path.cwd() / mem_file_name
                if mem_path.is_file():
                    mem_content = mem_path.read_text()
                    # Ensure there is a clear separation between memory content and the prompt
                    prompt = f"{mem_content}\n\n{prompt}"
            except Exception:
                # If any issue occurs (e.g., file not found), fall back to the original prompt
                pass

        return prompt

    def get_continuation_prompts(self) -> List[str]:
        """Get list of continuation prompts"""
        return self._prompts_data.get(
            "continuation_prompts",
            [
                "Continue from where you left off. Do not repeat what you've already written.",
            ],
        )

    def get_continuation_prompt(self, index: int = 0) -> str:
        """Get a specific continuation prompt by index (rotates)"""
        prompts = self.get_continuation_prompts()
        return prompts[index % len(prompts)]

    def get_tool_prompt(self, prompt_name: str) -> str:
        """Get a tool-specific prompt"""
        tool_prompts = self._prompts_data.get("tool_prompts", {})
        return tool_prompts.get(prompt_name, "")

    def get_git_prompt(self, prompt_name: str) -> str:
        """Get a git-related prompt (commit_analysis, pr_analysis, etc.)"""
        git_prompts = self._prompts_data.get("git_prompts", {})
        return git_prompts.get(prompt_name, "")

    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration (banned commands, confirm commands)"""
        return self._prompts_data.get(
            "security",
            {
                "banned_commands": [],
                "confirm_commands": [],
            },
        )

    def get_memory_config(self) -> Dict[str, Any]:
        """Get memory/CLAUDE.md configuration"""
        return self._prompts_data.get(
            "memory",
            {
                "memory_file": "CLAUDE.md",
                "memory_prompt": "",
            },
        )

    def get_persona(self) -> Dict[str, Any]:
        """Get persona configuration"""
        return self._prompts_data.get(
            "persona",
            {
                "name": "Hcode",
                "tone": "professional",
                "use_emojis": False,
                "verbosity": "balanced",
            },
        )

    def get_formatting(self) -> Dict[str, Any]:
        """Get formatting configuration"""
        return self._prompts_data.get(
            "formatting",
            {
                "code_block_style": "fenced",
                "default_language": "python",
                "show_line_numbers": True,
                "max_output_lines": 100,
            },
        )

    def get_claude_prompt(self) -> str:
        """
        Get the Claude Code style system prompt.

        Returns:
            Claude-style system prompt
        """
        return self.get_system_prompt("claude_code_style")

    def get_claude_reasoning_phase(self, phase_name: str) -> str:
        """
        Get a specific Claude reasoning phase template.

        Args:
            phase_name: Phase name (perception, comprehension, analysis, etc.)

        Returns:
            Reasoning phase template
        """
        phases = self._prompts_data.get("claude_reasoning_phases", {})
        return phases.get(phase_name, "")

    def get_claude_example(self, example_name: str) -> str:
        """
        Get a Claude-style interaction example.

        Args:
            example_name: Example identifier (simple_fix, complex_feature)

        Returns:
            Example interaction text
        """
        examples = self._prompts_data.get("claude_examples", {})
        return examples.get(example_name, "")

    def list_claude_reasoning_phases(self) -> List[str]:
        """
        List all available Claude reasoning phases.

        Returns:
            List of phase names
        """
        phases = self._prompts_data.get("claude_reasoning_phases", {})
        return list(phases.keys())

    def list_claude_examples(self) -> List[str]:
        """
        List all available Claude examples.

        Returns:
            List of example names
        """
        examples = self._prompts_data.get("claude_examples", {})
        return list(examples.keys())

    def get_reasoning_system_prompt(self) -> str:
        """
        Get the core reasoning system prompt.

        Returns:
            Reasoning system prompt string
        """
        return self._prompts_data.get("reasoning_prompts", {}).get("system", "")

    def get_reasoning_template(self, depth: str) -> str:
        """
        Get a thinking template for a specific depth (quick, standard, deep).

        Args:
            depth: depth name

        Returns:
            Thinking template string
        """
        return self._prompts_data.get("reasoning_prompts", {}).get("templates", {}).get(depth, "")

    def get_reasoning_enhancement(self, name: str) -> str:
        """
        Get an enhancement prompt (self_critique, uncertainty_handling, etc).

        Args:
            name: enhancement name

        Returns:
            Enhancement prompt string
        """
        return self._prompts_data.get("reasoning_prompts", {}).get("enhancements", {}).get(name, "")

    def get_reasoning_task_specific(self, task_name: str) -> str:
        """
        Get a task-specific reasoning protocol.

        Args:
            task_name: Task name (debugging, refactoring, etc)

        Returns:
            Task specific protocol string
        """
        return self._prompts_data.get("reasoning_prompts", {}).get("task_specific", {}).get(task_name, "")

    def get_phase_instruction(self, phase_name: str) -> str:
        """
        Get instruction for a specific reasoning phase.

        Args:
            phase_name: Name of the phase

        Returns:
            Instruction string
        """
        instructions = self._prompts_data.get("reasoning_prompts", {}).get("phase_instructions", {})
        return instructions.get(phase_name, "Think about this aspect of the problem.")



class ModelsConfig:
    """
    Centralized model configuration loader.

    Loads model parameters from config/models.yaml and provides
    easy access to generation settings.
    """

    _instance: Optional["ModelsConfig"] = None
    _models_data: Dict[str, Any] = {}
    _config_path: Optional[Path] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_models()
        return cls._instance

    def _find_config_path(self) -> Optional[Path]:
        """Find the models configuration file"""
        # Check environment variable first
        env_path = os.getenv("HCODE_MODELS_CONFIG")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        # Search paths in order of priority
        search_paths = [
            Path.cwd() / "config" / "models.yaml",
            Path.cwd() / "models.yaml",
            Path(__file__).parent.parent.parent.parent / "config" / "models.yaml",
            Path.home() / ".hcode" / "models.yaml",
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def _load_models(self):
        """Load model config from YAML file"""
        self._config_path = self._find_config_path()

        if self._config_path and self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._models_data = yaml.safe_load(f) or {}
        else:
            # Use default config if no file found
            self._models_data = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default model configuration"""
        return {
            "generation": {
                "temperature": 0.3,
                "top_p": 1.0,
                "top_k": 0,
                "max_tokens": 4096,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "stop_sequences": [],
            },
            "task_overrides": {},
            "context": {
                "max_context_tokens": 128000,
                "reserve_output_tokens": 8192,
                "summarization_threshold": 0.8,
                "max_history_turns": 50,
            },
            "continuation": {
                "enabled": True,
                "max_continuations": 10,
                "max_total_tokens": 100000,
            },
            "reliability": {
                "timeout": 120,
                "connect_timeout": 30,
                "max_retries": 5,
            },
        }

    def reload(self):
        """Reload configuration from file"""
        self._load_models()

    @property
    def config_path(self) -> Optional[Path]:
        """Get the path to the loaded config file"""
        return self._config_path

    def get_generation_params(self, task_type: Optional[str] = None) -> GenerationParams:
        """
        Get generation parameters, optionally for a specific task type.

        Args:
            task_type: Optional task type (code_generation, bug_fixing, etc.)

        Returns:
            GenerationParams instance
        """
        # Start with base generation params
        gen_config = self._models_data.get("generation", {})

        params = GenerationParams(
            temperature=gen_config.get("temperature", 0.3),
            top_p=gen_config.get("top_p", 1.0),
            top_k=gen_config.get("top_k", 0),
            max_tokens=gen_config.get("max_tokens", 16384),  # Maximum for most models
            frequency_penalty=gen_config.get("frequency_penalty", 0.0),
            presence_penalty=gen_config.get("presence_penalty", 0.0),
            stop_sequences=gen_config.get("stop_sequences", []),
        )

        # Apply task-specific overrides if specified
        if task_type:
            overrides = self._models_data.get("task_overrides", {}).get(task_type, {})
            if overrides:
                if "temperature" in overrides:
                    params.temperature = overrides["temperature"]
                if "top_p" in overrides:
                    params.top_p = overrides["top_p"]
                if "top_k" in overrides:
                    params.top_k = overrides["top_k"]
                if "max_tokens" in overrides:
                    params.max_tokens = overrides["max_tokens"]
                if "frequency_penalty" in overrides:
                    params.frequency_penalty = overrides["frequency_penalty"]
                if "presence_penalty" in overrides:
                    params.presence_penalty = overrides["presence_penalty"]

        return params

    def get_temperature(self, task_type: Optional[str] = None) -> float:
        """Get temperature setting"""
        return self.get_generation_params(task_type).temperature

    def get_top_p(self, task_type: Optional[str] = None) -> float:
        """Get top_p setting"""
        return self.get_generation_params(task_type).top_p

    def get_max_tokens(self, task_type: Optional[str] = None) -> int:
        """Get max_tokens setting"""
        return self.get_generation_params(task_type).max_tokens

    def get_context_config(self) -> ContextConfig:
        """Get context window configuration"""
        ctx = self._models_data.get("context", {})
        return ContextConfig(
            max_context_tokens=ctx.get("max_context_tokens", 128000),
            reserve_output_tokens=ctx.get("reserve_output_tokens", 8192),
            summarization_threshold=ctx.get("summarization_threshold", 0.8),
            max_history_turns=ctx.get("max_history_turns", 50),
        )

    def get_continuation_config(self) -> ContinuationConfig:
        """Get continuation configuration"""
        cont = self._models_data.get("continuation", {})
        return ContinuationConfig(
            enabled=cont.get("enabled", True),
            max_continuations=cont.get("max_continuations", 10),
            max_total_tokens=cont.get("max_total_tokens", 100000),
            truncation_patterns=cont.get("truncation_patterns", []),
        )

    def get_reliability_config(self) -> ReliabilityConfig:
        """Get reliability/retry configuration"""
        rel = self._models_data.get("reliability", {})
        return ReliabilityConfig(
            timeout=rel.get("timeout", 120.0),
            connect_timeout=rel.get("connect_timeout", 30.0),
            max_retries=rel.get("max_retries", 5),
            retry_multiplier=rel.get("retry_multiplier", 2.0),
            retry_min=rel.get("retry_min", 2.0),
            retry_max=rel.get("retry_max", 30.0),
        )

    def get_model_for_provider(self, provider: str, size: str = "medium") -> str:
        """
        Get model name for a provider and size.

        Args:
            provider: Provider name (anthropic, openai)
            size: Size alias (small, medium, large, fast, balanced, quality)

        Returns:
            Model name string
        """
        models = self._models_data.get("models", {})

        # Check aliases first
        aliases = models.get("aliases", {})
        if size in aliases and provider in aliases[size]:
            return aliases[size][provider]

        # Fall back to defaults
        defaults = models.get("defaults", {})
        return defaults.get(provider, "gpt-4o")

    def get_compatible_model(self, provider_hint: str, size: str = "medium") -> str:
        """
        Get model for OpenAI-compatible providers.

        Args:
            provider_hint: Provider name or base URL hint
            size: Size alias

        Returns:
            Model name string
        """
        models = self._models_data.get("models", {})
        compatible = models.get("compatible", {})

        # Try to match provider
        provider_lower = provider_hint.lower()
        for compat_name, sizes in compatible.items():
            if compat_name in provider_lower:
                return sizes.get(size, sizes.get("medium", ""))

        # Return empty if not found
        return ""


# Convenience functions for easy access
@lru_cache(maxsize=1)
def get_prompts_config() -> PromptsConfig:
    """Get the prompts configuration singleton"""
    return PromptsConfig()


@lru_cache(maxsize=1)
def get_models_config() -> ModelsConfig:
    """Get the models configuration singleton"""
    return ModelsConfig()


def get_system_prompt(prompt_type: str = "coding_agent") -> str:
    """Convenience function to get a system prompt"""
    return get_prompts_config().get_system_prompt(prompt_type)


def get_generation_params(task_type: Optional[str] = None) -> GenerationParams:
    """Convenience function to get generation parameters"""
    return get_models_config().get_generation_params(task_type)


def get_temperature(task_type: Optional[str] = None) -> float:
    """Convenience function to get temperature"""
    return get_models_config().get_temperature(task_type)


def get_max_tokens(task_type: Optional[str] = None) -> int:
    """Convenience function to get max tokens"""
    return get_models_config().get_max_tokens(task_type)


def reload_configs():
    """Reload all configuration files"""
    get_prompts_config().reload()
    get_models_config().reload()
    # Clear caches
    get_prompts_config.cache_clear()
    get_models_config.cache_clear()


def get_claude_prompt() -> str:
    """Convenience function to get Claude Code style prompt"""
    return get_prompts_config().get_claude_prompt()



def get_claude_reasoning_phase(phase_name: str) -> str:
    """Convenience function to get a Claude reasoning phase"""
    return get_prompts_config().get_claude_reasoning_phase(phase_name)


def get_reasoning_system_prompt() -> str:
    """Convenience function to get reasoning system prompt"""
    return get_prompts_config().get_reasoning_system_prompt()


def get_phase_instruction(phase_name: str) -> str:
    """Convenience function to get phase instruction"""
    return get_prompts_config().get_phase_instruction(phase_name)

