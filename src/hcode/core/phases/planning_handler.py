"""
Planning phase handler.

Responsible for:
- Deep analysis of user requirements
- Research and understanding of codebase
- Creating task.md with task breakdown (checkbox format with IDs)
- Creating implementation_plan.md with concrete steps
- Determining when planning is complete
"""

import re
import logging
from typing import List, Any, Dict, Optional
from pathlib import Path

from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult

# FileAction enum for HcodeDisplay tracking
try:
    from hcode.ui.hcode_display import FileAction
except ImportError:
    FileAction = None

logger = logging.getLogger(__name__)


class PlanningPhaseHandler(BasePhaseHandler):
    """
    Handler for the Planning phase of PEV workflow.

    Creates:
    - .hcode/task.md: Task understanding and subtasks with checkbox format
    - .hcode/implementation_plan.md: Implementation steps with file paths

    The planning phase follows this workflow:
    1. Deep analysis of user requirements
    2. Research codebase to identify relevant files
    3. Create task breakdown with trackable subtasks
    4. Create detailed implementation plan with:
       - Goal description
       - User review required items
       - Proposed changes grouped by component
       - Verification plan

    Transition criteria:
    - Both artifacts exist and have valid content
    - Plan has concrete steps with file paths
    - Agent confirms plan is ready for user review
    """

    phase_name = "planning"

    def get_required_artifacts(self) -> List[str]:
        """Get artifacts this phase should produce."""
        return ["task.md", "implementation_plan.md"]

    async def handle(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute planning phase.

        Steps:
        1. Check if artifacts already exist
        2. If not, perform deep analysis:
           a. Analyze user requirements
           b. Research codebase for relevant files
           c. Identify dependencies and affected components
        3. Generate task.md with structured breakdown
        4. Generate implementation_plan.md with concrete steps
        5. Execute any tool calls from AI response
        6. Validate artifacts
        7. Determine if ready to transition

        Args:
            context: Current agent context
            loop_controller: Loop controller

        Returns:
            PhaseResult with planning outcome
        """
        try:
            artifacts_created = []
            tool_results = []
            response = ""

            logger.info(f"Planning phase iteration {context.iteration} for task: {context.task[:50]}...")

            # ALWAYS regenerate artifacts for new tasks - never skip planning
            # This ensures fresh analysis for each user request

            # =====================================================================
            # DEEP ANALYSIS PHASE
            # Before creating artifacts, deeply understand:
            # 1. What the user is asking for
            # 2. What files/components are involved
            # 3. What the implementation approach should be
            # =====================================================================

            # Build deep analysis prompt
            analysis_prompt = self._build_analysis_prompt(context)

            # Generate AI response for deep analysis
            analysis_response = ""
            analysis_insights = {}

            if self.provider is not None:
                logger.info("Generating AI response for deep analysis...")

                # DISPLAY: Show what we're doing using modern UI
                self._display("Analyzing task requirements...", style="info")

                # Start thinking display if HcodeDisplay available
                if self._hcode_display:
                    self._hcode_display.start_thinking()

                analysis_response, analysis_tool_results = await self._generate_and_execute(
                    analysis_prompt,
                    context,
                    system_prompt=self._get_planning_system_prompt(context)
                )
                tool_results.extend(analysis_tool_results)

                # End thinking display
                if self._hcode_display:
                    self._hcode_display.end_thinking()

                # DISPLAY: Show the AI's analysis response to user
                if analysis_response and len(analysis_response) > 50:
                    # Display the response - show text portions normally
                    # Extract text (non-JSON) portions for display
                    text_response = self._extract_text_response(analysis_response)
                    if text_response:
                        self._display(text_response, style="default")
                    # Also show in thinking block for full context
                    if self._hcode_display:
                        self._hcode_display.display_thinking_block(analysis_response, phase="PLANNING")

                logger.info(f"Analysis response length: {len(analysis_response)}, tool_results: {len(analysis_tool_results)}")

                # Extract analysis insights
                analysis_insights = self._extract_analysis_insights(analysis_response)
                logger.debug(f"Extracted insights: {list(analysis_insights.keys())}")
            else:
                logger.warning("No AI provider configured for planning phase")
                self._display("No AI provider configured for planning!", style="error")

            # =====================================================================
            # ARTIFACT GENERATION PHASE
            # Generate planning artifacts with the analysis insights
            # =====================================================================

            # Build planning prompt with analysis insights
            planning_prompt = self._build_planning_prompt(context, analysis_insights)

            # Generate AI response for planning - AI should use Write tool to create artifacts
            if self.provider is not None:
                self._display("Creating implementation plan...", style="info")

                # Start thinking for planning
                if self._hcode_display:
                    self._hcode_display.start_thinking()

                response, planning_tool_results = await self._generate_and_execute(
                    planning_prompt,
                    context,
                    system_prompt=self._get_planning_system_prompt(context)
                )
                tool_results.extend(planning_tool_results)

                # End thinking display
                if self._hcode_display:
                    self._hcode_display.end_thinking()

                # DISPLAY: Show the AI's planning response to user
                if response and len(response) > 50:
                    # Extract and show text portions
                    text_response = self._extract_text_response(response)
                    if text_response:
                        self._display(text_response, style="default")
                    # Show in thinking block for context
                    if self._hcode_display:
                        self._hcode_display.display_thinking_block(response, phase="PLANNING")

                # Check if AI created artifacts via Write tool
                for result in planning_tool_results:
                    if result.get("success") and "task.md" in str(result.get("output", "")):
                        artifacts_created.append("task.md")
                        # Track file with HcodeDisplay using FileAction enum
                        if self._hcode_display and FileAction:
                            self._hcode_display.track_file(".hcode/task.md", FileAction.CREATED)
                    if result.get("success") and "implementation_plan.md" in str(result.get("output", "")):
                        artifacts_created.append("implementation_plan.md")
                        if self._hcode_display and FileAction:
                            self._hcode_display.track_file(".hcode/implementation_plan.md", FileAction.CREATED)

                # If AI didn't use Write tool, extract content and create manually
                if not self.artifact_manager.artifact_exists("task.md", context):
                    ai_task_content = self._extract_task_content(response)
                    if ai_task_content:
                        artifact_path = self.artifact_manager.create_artifact("task.md", ai_task_content, context)
                        self._display("Created task.md", style="success")
                        artifacts_created.append("task.md")
                        if self._hcode_display and FileAction:
                            self._hcode_display.track_file(".hcode/task.md", FileAction.CREATED)

                if not self.artifact_manager.artifact_exists("implementation_plan.md", context):
                    ai_plan_content = self._extract_plan_content(response)
                    if ai_plan_content:
                        artifact_path = self.artifact_manager.create_artifact("implementation_plan.md", ai_plan_content, context)
                        self._display("Created implementation_plan.md", style="success")
                        artifacts_created.append("implementation_plan.md")
                        if self._hcode_display and FileAction:
                            self._hcode_display.track_file(".hcode/implementation_plan.md", FileAction.CREATED)

            # Validate artifacts
            valid, error = self.validate_artifacts(context)

            if not valid:
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output=f"Planning phase validation failed: {error}",
                    artifacts_created=artifacts_created,
                    can_transition=False,
                    error=error,
                    metadata={
                        "tool_results": tool_results,
                        "analysis_insights": analysis_insights
                    },
                )

            # Check if can transition
            can_transition = self.can_transition_to_next(context)

            # If this is an exploration task, return the AI's response
            is_exploration = context.metadata.get("task_type") == "exploration"
            if is_exploration and response:
                output = response
            else:
                output = f"Planning phase complete. Created: {', '.join(artifacts_created) or 'no new artifacts'}"

            return PhaseResult(
                phase_name=self.phase_name,
                success=True,
                output=output,
                artifacts_created=artifacts_created,
                can_transition=can_transition,
                metadata={
                    "tool_results": tool_results,
                    "analysis_insights": analysis_insights,
                    "response": response
                },
            )

        except Exception as e:
            logger.exception(f"Planning phase failed: {e}")
            return PhaseResult(
                phase_name=self.phase_name,
                success=False,
                output=f"Planning phase failed: {str(e)}",
                can_transition=False,
                error=str(e),
            )

    def _get_planning_system_prompt(self, context: AgentContext) -> str:
        """
        Get system prompt for planning phase.

        Uses core prompts from phases.yaml.

        Args:
            context: Current agent context

        Returns:
            Complete system prompt for planning
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            # Get identity and tool format
            identity = loader.get_identity()
            tool_format = loader.get_tool_format()

            # Get planning instruction from core prompts
            planning_prompt = loader.build_planning_prompt(task=context.task)

            # Load artifact templates from perfect_prompts for reference
            artifact_templates = self._get_artifact_templates()

            # Build system prompt with identity, tool format, and templates
            system_base = f"""{identity}

{tool_format}

---

{planning_prompt}

---

## ARTIFACT REFERENCE TEMPLATES

Follow these templates EXACTLY when creating task.md and implementation_plan.md:

{artifact_templates}"""

            # Add context information
            context_info = f"""
## Hcode Context

Working Directory: {context.working_dir}
Artifact Directory: .hcode
Current Iteration: {context.iteration}

### PEV Workflow (ALWAYS ENFORCED)

The PEV (Planning → Execution → Verification) workflow is ALWAYS executed.
Every task goes through:

1. **PLANNING**: Create task.md and implementation_plan.md
2. **EXECUTION**: Implement the plan using tools
3. **VERIFICATION**: Test and create walkthrough.md

### CRITICAL: Communication Rules

**YOU MUST**:
1. Provide TEXT explanations of what you're doing
2. Use JSON tool calls in code blocks for file operations
3. Summarize your findings and progress in plain text

### TOOL CALL FORMAT (CRITICAL!)

When you need to use a tool, output JSON in this EXACT format inside a code block:

```json
{{"tool": "ToolName", "arguments": {{"param": "value"}}}}
```

**Available tools:**
- LS: `{{"tool": "LS", "arguments": {{"DirectoryPath": "."}}}}`
- Read: `{{"tool": "Read", "arguments": {{"AbsolutePath": "/full/path"}}}}`
- Write: `{{"tool": "Write", "arguments": {{"TargetFile": "/full/path", "CodeContent": "content"}}}}`
- Edit: `{{"tool": "Edit", "arguments": {{"TargetFile": "/path", "TargetContent": "old", "ReplacementContent": "new"}}}}`
- Glob: `{{"tool": "Glob", "arguments": {{"Pattern": "**/*.py"}}}}`
- Grep: `{{"tool": "Grep", "arguments": {{"Query": "pattern", "SearchPath": "."}}}}`

### Example Good Response:

I'll help you create a script to count markdown files.

First, let me explore the project structure:

```json
{{"tool": "LS", "arguments": {{"DirectoryPath": "."}}}}
```

I found several directories. Now I'll create the planning artifacts:

```json
{{"tool": "Write", "arguments": {{"TargetFile": "{context.working_dir}/.hcode/task.md", "CodeContent": "# Task\\n\\nCreate a script to count .md files.\\n\\n## Subtasks\\n\\n- [ ] Create script <!-- id: 0 -->\\n- [ ] Test script <!-- id: 1 -->"}}}}
```

Planning complete! I've created task.md with the task breakdown.
"""
            return system_base + context_info

        except Exception as e:
            logger.warning(f"Failed to load core prompts: {e}")
            # Fallback to basic prompt
            return f"""You are Hcode, an AI coding assistant in PLANNING mode.

Your task: {context.task}

Working Directory: {context.working_dir}

## Instructions

1. Analyze the user's request
2. Explore the codebase using tools (LS, Glob, Read)
3. Create .hcode/task.md with task breakdown
4. Create .hcode/implementation_plan.md with implementation approach

IMPORTANT: Always provide text explanations along with tool usage.
DO NOT just output JSON silently.
"""

    def _build_analysis_prompt(self, context: AgentContext) -> str:
        """
        Build prompt for deep analysis phase.

        This prompt instructs the AI to:
        1. Understand the user's requirements in depth
        2. Research the codebase to identify relevant files
        3. Identify dependencies and affected components
        4. Note any ambiguities or questions

        Args:
            context: Current agent context

        Returns:
            Analysis prompt
        """
        return f"""## DEEP ANALYSIS PHASE

You are in PLANNING mode. Before creating any artifacts, you must deeply analyze the user's request.

### THINKING PROTOCOL

Before taking ANY action, you MUST think through:

<thinking>
=== COMPREHENSION ===
What is the user explicitly asking for?
What are the implicit requirements I should infer?
What would success look like for this task?

=== KNOWLEDGE ASSESSMENT ===
What do I already know about this codebase?
What information gaps do I need to fill?
What assumptions am I making that I should verify?

=== EXPLORATION STRATEGY ===
What tools should I use to gather information?
In what order should I explore?
What patterns or keywords should I search for?

=== RISK ASSESSMENT ===
What could go wrong with my approach?
What edge cases should I consider?
Are there any dependencies I might miss?
</thinking>

### USER REQUEST:
{context.task}

### ANALYSIS INSTRUCTIONS:

**Step 1: Requirement Understanding (THINK DEEPLY)**
Think step-by-step:
- What is the user asking for specifically? List all explicit requirements.
- What is the expected outcome? Define success criteria.
- What implicit requirements can you infer? Consider usability, maintainability, performance.
- What constraints exist? Time, compatibility, dependencies.

**Step 2: Codebase Research (USE TOOLS SYSTEMATICALLY)**
Before reading files, think about what you're looking for:
- Use `Glob` to find files matching patterns (e.g., "**/*.py" for Python files)
- Use `Grep` to search for specific code patterns, imports, class names
- Use `Read` to examine files you've identified as relevant
- Use `LS` to understand directory structure

IMPORTANT: Do NOT assume file contents. Always READ before making claims.

**Step 3: Identify Components (MAP DEPENDENCIES)**
Create a mental map:
- Which files will need to be modified? (List with reasons)
- Which files will need to be created? (Describe purpose)
- Are there any files that should be deleted?
- What are the dependencies between components?
- What is the order of changes (what depends on what)?

**Step 4: Hypothesis Formation**
Form and test hypotheses:
- "I believe the change should be made in X because Y"
- "I expect to find Z in file W"
- Test each hypothesis by reading/searching

**Step 5: Note Ambiguities (BE EXPLICIT)**
- What questions would you ask the user if you could?
- What alternative approaches exist?
- What tradeoffs are involved?

### OUTPUT FORMAT:

After your research, provide a comprehensive summary:

<analysis>
## Understanding

### Explicit Requirements
[Bullet points of what user explicitly asked for]

### Implicit Requirements
[What the user probably also needs/expects]

### Success Criteria
[How we'll know the task is complete]

## Relevant Files

### Files to Modify
- `file1.py`: [detailed reason why it's relevant, what changes needed]
- `file2.py`: [detailed reason why it's relevant, what changes needed]

### Files to Create (if any)
- `newfile.py`: [purpose and contents overview]

### Files to Reference (read-only)
- `file3.py`: [why we need to understand this file]

## Components Affected

### Component 1: [Name]
- Current behavior: [description]
- Required changes: [what needs to change]
- Impact: [what else this affects]

### Component 2: [Name]
- Current behavior: [description]
- Required changes: [what needs to change]
- Impact: [what else this affects]

## Dependencies

### Internal Dependencies
- [module A depends on module B]

### External Dependencies
- [any external packages needed]

### Change Order
1. First change X (because Y depends on it)
2. Then change Y
3. Finally update Z

## Questions/Ambiguities

- [Question 1]: [Why it matters]
- [Question 2]: [Why it matters]

## Recommended Approach

### Strategy
[High-level approach description]

### Rationale
[Why this approach over alternatives]

### Risks & Mitigations
- Risk 1: [description] -> Mitigation: [how to handle]
- Risk 2: [description] -> Mitigation: [how to handle]
</analysis>

NOW BEGIN YOUR ANALYSIS. Use tools to research the codebase. THINK before each tool use."""

    def _build_planning_prompt(
        self,
        context: AgentContext,
        analysis_insights: Dict[str, Any]
    ) -> str:
        """
        Build prompt for planning phase with analysis insights.

        Args:
            context: Current agent context
            analysis_insights: Insights from deep analysis phase

        Returns:
            Planning prompt
        """
        # Get template formats
        task_template_guide = self._get_task_template_guide()
        plan_template_guide = self._get_plan_template_guide()

        # Build insights summary
        insights_summary = ""
        if analysis_insights:
            if analysis_insights.get("understanding"):
                insights_summary += f"\n### Understanding:\n{analysis_insights['understanding']}\n"
            if analysis_insights.get("relevant_files"):
                files_list = "\n".join(f"- {f}" for f in analysis_insights["relevant_files"])
                insights_summary += f"\n### Relevant Files:\n{files_list}\n"
            if analysis_insights.get("approach"):
                insights_summary += f"\n### Recommended Approach:\n{analysis_insights['approach']}\n"

        return f"""## PLANNING ARTIFACT GENERATION

Based on your analysis, now create the planning artifacts.

### USER REQUEST:
{context.task}

### ANALYSIS INSIGHTS:
{insights_summary or "(No analysis insights available - use your best judgment)"}

### ARTIFACT 1: task.md

Create a task.md file following this format:

{task_template_guide}

**CRITICAL RULES for task.md:**
1. Use checkbox format: `- [ ]`, `- [/]`, `- [x]`
2. Add unique IDs: `<!-- id: 0 -->`, `<!-- id: 1 -->`, etc.
3. Break down complex tasks into subtasks (indented)
4. Start with high-level tasks, then add details

### ARTIFACT 2: implementation_plan.md

Create an implementation_plan.md following this format:

{plan_template_guide}

**CRITICAL RULES for implementation_plan.md:**
1. Group changes by component
2. Include file paths with [MODIFY], [NEW], [DELETE] markers
3. Be specific about what will change in each file
4. Include a concrete verification plan with exact commands

### OUTPUT INSTRUCTIONS:

1. First, use the Write tool to create `.hcode/task.md`
2. Then, use the Write tool to create `.hcode/implementation_plan.md`
3. After creating both files, confirm they are ready for review

NOW CREATE THE ARTIFACTS using the Write tool."""

    def _get_task_template_guide(self) -> str:
        """Get task.md template guide."""
        return """```markdown
# Task

[User's original request]

## Subtasks

- [ ] Task 1 <!-- id: 0 -->
- [ ] Task 2 <!-- id: 1 -->
  - [ ] Subtask 2.1 <!-- id: 2 -->
  - [ ] Subtask 2.2 <!-- id: 3 -->
- [ ] Task 3 <!-- id: 4 -->

## Notes

[Any notes or findings]
```"""

    def _get_plan_template_guide(self) -> str:
        """Get implementation_plan.md template guide."""
        return """```markdown
# [Goal Description]

Brief description of the problem and what the change accomplishes.

## User Review Required

> [!IMPORTANT]
> Critical items needing user approval

## Proposed Changes

### [Component Name]

Summary of changes to this component

#### [MODIFY] [filename.py](file:///absolute/path/to/file.py)

- What will change in this file

#### [NEW] [newfile.py](file:///absolute/path/to/newfile.py)

- What this new file will contain

## Verification Plan

### Automated Tests
- Exact command: `pytest tests/specific_test.py -v`

### Manual Verification
- Steps to verify manually
```"""

    def _extract_analysis_insights(self, response: str) -> Dict[str, Any]:
        """
        Extract analysis insights from AI response.

        Parses the <analysis> block from the AI's deep analysis.

        Args:
            response: AI response containing analysis

        Returns:
            Dict with extracted insights
        """
        insights = {
            "understanding": "",
            "relevant_files": [],
            "components": [],
            "dependencies": [],
            "questions": [],
            "approach": "",
        }

        if not response:
            return insights

        # Try to extract analysis block
        analysis_match = re.search(
            r'<analysis>(.*?)</analysis>',
            response,
            re.DOTALL | re.IGNORECASE
        )

        if analysis_match:
            analysis_content = analysis_match.group(1)
        else:
            # Use full response if no block found
            analysis_content = response

        # Extract understanding section
        understanding_match = re.search(
            r'##\s*Understanding\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if understanding_match:
            insights["understanding"] = understanding_match.group(1).strip()

        # Extract relevant files
        files_match = re.search(
            r'##\s*Relevant Files?\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if files_match:
            files_text = files_match.group(1)
            file_lines = re.findall(r'-\s*([^\n:]+)', files_text)
            insights["relevant_files"] = [f.strip() for f in file_lines if f.strip()]

        # Extract components
        components_match = re.search(
            r'##\s*Components?\s*(?:Affected)?\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if components_match:
            components_text = components_match.group(1)
            component_lines = re.findall(r'-\s*([^\n]+)', components_text)
            insights["components"] = [c.strip() for c in component_lines if c.strip()]

        # Extract approach
        approach_match = re.search(
            r'##\s*(?:Recommended\s*)?Approach\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if approach_match:
            insights["approach"] = approach_match.group(1).strip()

        # Extract questions/ambiguities
        questions_match = re.search(
            r'##\s*(?:Questions?|Ambiguities?)\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if questions_match:
            questions_text = questions_match.group(1)
            question_lines = re.findall(r'-\s*([^\n]+)', questions_text)
            insights["questions"] = [q.strip() for q in question_lines if q.strip()]

        return insights

    def _extract_task_content(self, response: str) -> Optional[str]:
        """
        Extract task.md content from AI response.

        Looks for markdown content with checkbox format.

        Args:
            response: AI response text

        Returns:
            Extracted task content or None
        """
        if not response:
            return None

        # Look for task.md content markers
        task_pattern = r'(?:```(?:markdown)?[^\n]*\n)?(#\s*Task[^`]*(?:- \[[ x/]\][^\n]+\n)+)'
        match = re.search(task_pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        # Look for checklist items with IDs
        if "- [ ]" in response and "<!-- id:" in response:
            lines = response.split("\n")
            task_lines = []
            capture = False
            for line in lines:
                if "# Task" in line or "## Task" in line:
                    capture = True
                    task_lines.append(line)
                elif capture and (line.startswith("- [") or line.startswith("  - [")):
                    task_lines.append(line)
                elif capture and line.startswith("#"):
                    if "Implementation" not in line:
                        task_lines.append(line)
                    else:
                        break
            if task_lines:
                return "\n".join(task_lines)

        # Standard checkbox format without IDs
        if "- [ ]" in response or "- [x]" in response:
            lines = response.split("\n")
            task_lines = []
            capture = False
            for line in lines:
                if "# Task" in line or "## Task" in line:
                    capture = True
                    task_lines.append(line)
                elif capture and (line.startswith("- [") or line.startswith("  - [")):
                    task_lines.append(line)
                elif capture and line.startswith("#"):
                    break
            if task_lines:
                return "\n".join(task_lines)

        return None

    def _extract_plan_content(self, response: str) -> Optional[str]:
        """
        Extract implementation_plan.md content from AI response.

        Looks for markdown content with implementation plan structure.

        Args:
            response: AI response text

        Returns:
            Extracted plan content or None
        """
        if not response:
            return None

        # Look for implementation plan content markers
        plan_pattern = r'(?:```(?:markdown)?[^\n]*\n)?(#\s*(?:Implementation Plan|Goal)[^`]*(?:##[^`]*)+)'
        match = re.search(plan_pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        # Look for plan structure
        if "## Proposed Changes" in response or "## Verification Plan" in response:
            lines = response.split("\n")
            plan_lines = []
            capture = False
            for line in lines:
                if "# Implementation" in line or "# Goal" in line:
                    capture = True
                    plan_lines.append(line)
                elif capture:
                    plan_lines.append(line)
            if plan_lines:
                return "\n".join(plan_lines)

        return None

    # NOTE: Template methods removed - AI must generate all content directly

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """
        Check if ready to transition to execution phase.

        Criteria:
        - Both task.md and implementation_plan.md exist
        - Both have valid content
        - Plan has concrete steps (not just placeholders)

        Args:
            context: Current agent context

        Returns:
            True if planning is complete
        """
        # Check if required artifacts exist
        if not self.artifact_manager.artifact_exists("task.md", context):
            return False

        if not self.artifact_manager.artifact_exists("implementation_plan.md", context):
            return False

        # Validate content
        valid, _ = self.validate_artifacts(context)
        if not valid:
            return False

        # Check plan has concrete steps
        plan_content = self.artifact_manager.load_artifact("implementation_plan.md", context)
        if plan_content:
            # Should have at least one file path or concrete change
            has_concrete_steps = (
                "file://" in plan_content or
                "[MODIFY]" in plan_content or
                "[NEW]" in plan_content or
                "####" in plan_content
            )
            if not has_concrete_steps:
                return False

        return True

    def _get_artifact_templates(self) -> str:
        """
        Get artifact templates from perfect_prompts directory.

        These templates provide guidelines for creating high-quality
        task.md and implementation_plan.md files.

        Returns:
            Combined templates as a string
        """
        try:
            from hcode.config.perfect_prompts import get_perfect_prompt_loader
            loader = get_perfect_prompt_loader()

            task_template = loader.get_raw("task") or ""
            plan_template = loader.get_raw("implementation_plan") or ""

            if task_template or plan_template:
                templates = []
                if task_template:
                    templates.append("### task.md Template\n\n" + task_template)
                if plan_template:
                    templates.append("### implementation_plan.md Template\n\n" + plan_template)
                return "\n\n---\n\n".join(templates)

        except Exception as e:
            logger.warning(f"Failed to load artifact templates: {e}")

        # Fallback to embedded templates
        return """### task.md Template

Use this format for task.md:
- [ ] for uncompleted tasks
- [/] for in progress tasks
- [x] for completed tasks
- Add unique IDs: <!-- id: 0 -->, <!-- id: 1 -->, etc.
- Add subtasks by indenting under parent tasks
- Update CONSTANTLY as you work
- Mark tasks as completed immediately when done

Example:
```markdown
# Task

[User's request here]

## Subtasks

- [/] Research the codebase <!-- id: 0 -->
- [ ] Implement the feature <!-- id: 1 -->
  - [ ] Create main file <!-- id: 2 -->
  - [ ] Add tests <!-- id: 3 -->
- [ ] Verify implementation <!-- id: 4 -->

## Notes

[Any findings or notes]
```

### implementation_plan.md Template

Use this format for implementation_plan.md:

```markdown
# [Goal Description]

Provide a brief description of the problem and what the change accomplishes.

## User Review Required

> [!IMPORTANT]
> Any critical items needing user approval

## Proposed Changes

### [Component Name]

Summary of what will change

#### [NEW] [filename](file:///absolute/path)
- What this new file will contain

#### [MODIFY] [filename](file:///absolute/path)
- What will change in this file

## Verification Plan

### Automated Tests
- Exact commands to run: `pytest tests/test_file.py`

### Manual Verification
- Steps to verify manually
```

Critical Rules:
- Use file basenames as link text, not full paths
- Group changes by component
- Be specific about what changes in each file
- Include concrete test commands
"""
