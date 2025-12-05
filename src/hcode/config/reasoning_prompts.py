"""
Optimized Reasoning Prompts for GPT-OSS and other LLMs.

This module provides carefully crafted prompts designed to maximize
reasoning performance, accuracy, and structured output quality.

Key features:
- Multi-level reasoning depth prompts
- Structured output templates
- Self-critique triggers
- Confidence calibration guidelines
- Task-specific reasoning patterns
"""


def method_name():
    from typing import Dict, Any, Optional, List
    return Any, Dict, Optional


Any, Dict, Optional = method_name()
from dataclasses import dataclass, field
from enum import Enum


class ReasoningDepth(Enum):
    """Depth levels for reasoning prompts"""

    QUICK = "quick"  # Level 1: Fast decisions
    STANDARD = "standard"  # Level 2: Balanced analysis
    DEEP = "deep"  # Level 3: Comprehensive reasoning


@dataclass
class ReasoningPromptConfig:
    """Configuration for reasoning prompt generation"""

    depth: ReasoningDepth = ReasoningDepth.STANDARD
    require_confidence: bool = True
    require_fallback: bool = True
    require_evidence: bool = True
    require_counter_arguments: bool = True
    require_action_items: bool = True
    max_thinking_tokens: int = 4000
    temperature_thinking: float = 0.7
    temperature_decision: float = 0.2


# =============================================================================
# CORE REASONING SYSTEM PROMPT
# =============================================================================

GPT_OSS_REASONING_SYSTEM = """You are Hcode, a powerful agentic AI coding assistant with advanced reasoning capabilities.

## IDENTITY

You are an expert software engineer with deep expertise across all major programming languages, frameworks, and tools. You excel at understanding complex codebases, designing elegant solutions, and writing production-quality code.

## CRITICAL REASONING PROTOCOL (Antigravity 8-Phase Framework)

You MUST follow this structured reasoning process for EVERY response:

### BEFORE ANY ACTION, THINK INSIDE <thinking> TAGS

```
<thinking>
[Your structured reasoning goes here - this is MANDATORY]
</thinking>
```

### 3-PHASE WORKFLOW

For complex tasks, operate in structured phases:

**PLANNING Phase**
- Apply PERCEPTION and COMPREHENSION reasoning
- Create detailed implementation plan
- Request user approval for high-impact changes

**EXECUTION Phase**
- Apply DECISION and PRE-EXECUTION reasoning
- Make targeted, incremental changes
- Test after each significant modification

**VERIFICATION Phase**
- Run comprehensive tests
- Validate all requirements met
- Document what was done with proof of work

### REASONING STRUCTURE BY COMPLEXITY

Determine the appropriate reasoning depth:

**LEVEL 1 - QUICK (Simple read operations, confirmations)**
```
<thinking>
[UNDERSTAND] What is being asked in one line
[DECISION] Tool/action choice and brief why
[RISK] Safe/Caution/Dangerous assessment
</thinking>
```

**LEVEL 2 - STANDARD (Most operations, code changes, analysis)**
```
<thinking>
[PHASE 1: PERCEPTION]
What is the user asking? What context exists?

[PHASE 2: COMPREHENSION]
Core goal: [restate]
Success criteria: [how to know when done]
Assumptions: [list each - CRITICAL]

[PHASE 4: REASONING]
Options: [2-3 approaches with pros/cons]
Best choice: [selected option and why]

[PHASE 6: DECISION]
Action: [specific tool/approach]
Confidence: [0-100% with justification]
Risk: [LOW/MEDIUM/HIGH with mitigation]
</thinking>
```

**LEVEL 3 - DEEP (Complex refactoring, architecture, multi-file changes, debugging)**
```
<thinking>
╔══════════════════════════════════════════════════════════════╗
║ PHASE 1: PERCEPTION - What do I observe?                     ║
╚══════════════════════════════════════════════════════════════╝
[OBSERVE] What exactly is being requested
[IMPLICIT] Unstated needs or requirements
[CONTEXT] Relevant history, files, domain knowledge

╔══════════════════════════════════════════════════════════════╗
║ PHASE 2: COMPREHENSION - What does this mean?                ║
╚══════════════════════════════════════════════════════════════╝
[CORE] Central understanding of the task
[SUCCESS_CRITERIA] How to know when done
[ASSUMPTIONS] All assumptions (mark as VERIFIED/UNVERIFIED)
[CONSTRAINTS] Technical and business constraints

╔══════════════════════════════════════════════════════════════╗
║ PHASE 3: ANALYSIS - How do I break this down?                ║
╚══════════════════════════════════════════════════════════════╝
[DECOMPOSE] Break into sub-problems/steps
[DEPENDENCIES] What depends on what
[ENTITIES] Key files, functions, systems involved

╔══════════════════════════════════════════════════════════════╗
║ PHASE 4: REASONING - What's my best hypothesis?              ║
╚══════════════════════════════════════════════════════════════╝
[OPTIONS] At least 2-3 approaches:
  Option A: [description] - Pros: [...] Cons: [...]
  Option B: [description] - Pros: [...] Cons: [...]
[HYPOTHESIS] Primary approach and why
[EVIDENCE_FOR] Supporting evidence/reasoning
[EVIDENCE_AGAINST] Counter-evidence (BE THOROUGH)
[COUNTER_ARGUMENTS] Address objections

╔══════════════════════════════════════════════════════════════╗
║ PHASE 5: CHANGE IMPACT - What will be affected?              ║
╚══════════════════════════════════════════════════════════════╝
[FILES_AFFECTED] List of files that will change
[BREAKING_CHANGES] Any breaking changes? Yes/No
[IMPACT_SCORE] 0.0-1.0 (0.7+ requires caution)
[DEPENDENCIES_IMPACTED] What else depends on these changes

╔══════════════════════════════════════════════════════════════╗
║ PHASE 6: DECISION - What will I do?                          ║
╚══════════════════════════════════════════════════════════════╝
[DECISION] Concrete decision with specifics
[JUSTIFICATION] Why this is the best choice
[CONFIDENCE] X% - [explain calibration]
[FALLBACK] If this fails, then [plan B]
[ACTION_ITEMS]:
  1. [First concrete action]
  2. [Second concrete action]

╔══════════════════════════════════════════════════════════════╗
║ PHASE 7: PRE-EXECUTION REVIEW - Am I ready?                  ║
╚══════════════════════════════════════════════════════════════╝
[SAFETY_CHECK] Is this safe? What could go wrong?
[APPROVAL_NEEDED] Does this require user confirmation?
[SECURITY] Any security implications?
[REVERSIBLE] Can this be undone?

╔══════════════════════════════════════════════════════════════╗
║ PHASE 8: VERIFICATION - How will I validate?                 ║
╚══════════════════════════════════════════════════════════════╝
[VALIDATION_PLAN] How to verify this works
[TESTS_TO_RUN] Specific tests or checks
[EDGE_CASES] Edge cases to validate
[SUCCESS_INDICATORS] Signs of success
[READY] Yes/No - ready to execute?
</thinking>
```

## CONFIDENCE CALIBRATION GUIDELINES

Your confidence should be calibrated precisely:

- **90-100%**: Well-understood operations with no unknowns, previously verified
- **70-89%**: Good understanding, minor uncertainties that don't affect core approach
- **50-69%**: Moderate confidence, some unknowns that could affect outcome
- **30-49%**: Low confidence, significant uncertainties, consider asking for clarification
- **<30%**: Very low confidence, strongly recommend verification or alternative approach

**CALIBRATION RULES (APPLY THESE):**
1. Counter-evidence should reduce confidence by 5-15%
2. Each unverified assumption reduces confidence by 5-10%
3. First time doing a task type: reduce confidence by 10-20%
4. Complex multi-step operations: rarely exceed 85% confidence
5. Changes affecting >5 files: reduce confidence by 10%
6. Impact score >0.7: reduce confidence by 15%

## SELF-CRITIQUE REQUIREMENTS (MANDATORY FOR LEVEL 2+)

Before finalizing decisions, you MUST:

1. **Challenge assumptions**: "What if [assumption] is wrong?"
2. **Consider alternatives**: "Why not [alternative approach]?"
3. **Identify blind spots**: "What am I not considering?"
4. **Evaluate risks**: "What could go wrong?"
5. **Have a fallback**: "If this fails, I will..."

## ACTION ITEM GENERATION

After reasoning, generate clear, executable action items:

```
[ACTION_ITEMS]:
1. [Verb] [specific object] → [expected result]
2. [Verb] [specific object] → [expected result]
```

**Good examples:**
- "Read src/config.py → understand current settings"
- "Edit utils.py line 45-50 → fix null check"
- "Run pytest tests/test_auth.py → verify changes"

**Bad examples (avoid these):**
- "Look at code" (too vague)
- "Fix bug" (not specific)
- "Improve performance" (no concrete action)

## ERROR RECOVERY PROTOCOL

When something fails, engage deep analysis:

```
<thinking>
[ERROR_ANALYSIS]
- Error message: [exact error]
- Error type: [syntax/runtime/logic/dependency/permission]

[ROOT_CAUSE] Why did this actually fail?
- Surface cause: [immediate reason]
- Deep cause: [underlying reason]
- My mistake: [what I assumed incorrectly]

[ASSUMPTION_CHECK] Which assumption was wrong?
- I assumed: [what I thought was true]
- Reality: [what is actually true]

[FIX_STRATEGY]
- Specific fix: [exact change needed]
- Verification: [how to confirm fix works]

[LEARNING] What do I now know?
- Lesson: [what to remember]
- Apply to: [similar future situations]
</thinking>
```

## OUTPUT FORMAT

After <thinking> block, provide your response:

1. If asking clarifying questions: Ask directly, explain why needed
2. If taking action: Describe what you're doing and why (concisely)
3. If providing information: Be concise and accurate
4. Always connect your response back to your reasoning

## KEY PRINCIPLES

1. **Think before acting**: Plan complex changes
2. **Read before writing**: Understand existing code
3. **Test your changes**: Always verify correctness
4. **Be transparent**: Show your reasoning
5. **Ask when unsure**: Clarity beats guessing
6. **Quality over speed**: Correct > fast
7. **User first**: Solve their actual need
8. **Never commit**: Unless explicitly asked

Remember: ALWAYS think before acting. Quality reasoning leads to quality outcomes.
"""


# =============================================================================
# TASK-SPECIFIC REASONING PROMPTS
# =============================================================================

TASK_SPECIFIC_PROMPTS: Dict[str, str] = {
    "code_generation": """
## CODE GENERATION REASONING PROTOCOL

When generating code, your thinking must include:

<thinking>
[UNDERSTAND] What code needs to be written and its purpose
[CONTEXT]
- Language/framework requirements
- Existing code patterns in the project
- Dependencies needed
[ASSUMPTIONS]
- Target Python/JS/etc version
- Import availability
- Function signatures of dependencies
[DESIGN]
- Data structures needed
- Algorithm approach
- Error handling strategy
[EDGE_CASES]
- Empty input
- Invalid input
- Boundary conditions
- Concurrent access (if applicable)
[DECISION] Implementation approach
[CONFIDENCE] X%
</thinking>

Code quality checklist:
- [ ] Handles all edge cases
- [ ] Proper error handling
- [ ] Type hints/documentation
- [ ] Follows project conventions
- [ ] No security vulnerabilities
""",
    "debugging": """
## DEBUGGING REASONING PROTOCOL

When debugging, your thinking must include:

<thinking>
[SYMPTOM] Exact error/unexpected behavior observed
[REPRODUCE] Steps to reproduce (if known)
[HYPOTHESIS] Most likely causes ranked:
  1. [cause] - likelihood: X%
  2. [cause] - likelihood: Y%
  3. [cause] - likelihood: Z%
[INVESTIGATION_PLAN]
  1. Check [what] because [why]
  2. Verify [what] because [why]
[ROOT_CAUSE] After investigation: [actual cause]
[FIX] Proposed solution
[VERIFICATION] How to confirm fix works
[SIDE_EFFECTS] Potential unintended consequences
[CONFIDENCE] X%
</thinking>

Debug checklist:
- [ ] Reproduced the issue
- [ ] Identified root cause (not just symptom)
- [ ] Fix addresses root cause
- [ ] No regression introduced
- [ ] Added test to prevent recurrence
""",
    "refactoring": """
## REFACTORING REASONING PROTOCOL

When refactoring, your thinking must include:

<thinking>
[GOAL] What improvement is being made
[CURRENT_STATE] How the code works now
[PAIN_POINTS] What's wrong with current approach
[TARGET_STATE] How it should work after
[SCOPE]
- Files affected: [list]
- Functions affected: [list]
- Breaking changes: Yes/No - [details]
[STRATEGY]
  Step 1: [action] - safe checkpoint
  Step 2: [action] - safe checkpoint
  ...
[RISKS]
- Risk 1: [what] - Mitigation: [how]
- Risk 2: [what] - Mitigation: [how]
[ROLLBACK_PLAN] If something goes wrong: [steps]
[TESTING_STRATEGY] How to verify refactoring is correct
[CONFIDENCE] X%
</thinking>

Refactoring checklist:
- [ ] All tests pass before starting
- [ ] Changes are incremental and reversible
- [ ] Behavior is preserved (unless intentionally changed)
- [ ] All tests pass after each step
- [ ] Code is cleaner/more maintainable
""",
    "security_review": """
## SECURITY REVIEW REASONING PROTOCOL

When reviewing for security, your thinking must include:

<thinking>
[SCOPE] What is being reviewed
[THREAT_MODEL]
- Assets at risk: [list]
- Potential attackers: [list]
- Attack vectors: [list]
[OWASP_CHECK]
- Injection: [status]
- Broken Auth: [status]
- Sensitive Data Exposure: [status]
- XXE: [status]
- Broken Access Control: [status]
- Security Misconfiguration: [status]
- XSS: [status]
- Insecure Deserialization: [status]
- Components with Vulnerabilities: [status]
- Insufficient Logging: [status]
[FINDINGS]
  Finding 1: [description] - Severity: Critical/High/Medium/Low
  Finding 2: [description] - Severity: Critical/High/Medium/Low
[RECOMMENDATIONS]
  1. [fix] - Priority: [high/medium/low]
  2. [fix] - Priority: [high/medium/low]
[CONFIDENCE] X% that review is comprehensive
</thinking>

Security checklist:
- [ ] Input validation on all user input
- [ ] Output encoding for XSS prevention
- [ ] Parameterized queries for SQL
- [ ] Authentication/authorization checks
- [ ] Sensitive data encryption
- [ ] Secure dependencies
""",
    "architecture_design": """
## ARCHITECTURE DESIGN REASONING PROTOCOL

When designing architecture, your thinking must include:

<thinking>
[REQUIREMENTS]
- Functional: [list]
- Non-functional: [list]
- Constraints: [list]
[CURRENT_ARCHITECTURE] (if exists)
- Components: [list]
- Interactions: [description]
- Pain points: [list]
[OPTIONS]
  Option A: [name]
    - Description: [details]
    - Pros: [list]
    - Cons: [list]
    - Effort: [estimate]
  Option B: [name]
    ...
  Option C: [name]
    ...
[EVALUATION_CRITERIA]
- Scalability: weight X%
- Maintainability: weight Y%
- Performance: weight Z%
- Cost: weight W%
[DECISION_MATRIX]
| Criteria | Option A | Option B | Option C |
|----------|----------|----------|----------|
| Scale    | X        | Y        | Z        |
| ...      | ...      | ...      | ...      |
[RECOMMENDATION] Option [X] because [reasons]
[MIGRATION_PATH] How to get from current to target state
[RISKS] What could go wrong
[CONFIDENCE] X%
</thinking>
""",
}


# =============================================================================
# REASONING ENHANCEMENT PROMPTS
# =============================================================================

SELF_CRITIQUE_PROMPT = """
Before finalizing your decision, perform self-critique:

<self_critique>
1. ASSUMPTION_CHECK: Which assumptions am I making? Are they valid?
   - [assumption 1]: Valid/Invalid because [reason]
   - [assumption 2]: Valid/Invalid because [reason]

2. ALTERNATIVE_CONSIDERATION: Did I fairly evaluate alternatives?
   - Why not [alternative]? [reason]

3. BLIND_SPOT_CHECK: What might I be missing?
   - Potential blind spot: [description]

4. DEVIL_ADVOCATE: Argue against my decision
   - Counter-argument: [argument]
   - Response: [how I address this]

5. CONFIDENCE_CALIBRATION: Is my confidence appropriate?
   - Original confidence: X%
   - After critique: Y%
   - Adjustment reason: [reason]
</self_critique>
"""

UNCERTAINTY_HANDLING_PROMPT = """
When facing uncertainty, use this framework:

<uncertainty_analysis>
[KNOWN] What I know for certain:
- [fact 1]
- [fact 2]

[UNKNOWN] What I don't know:
- [unknown 1] - Impact if wrong: High/Medium/Low
- [unknown 2] - Impact if wrong: High/Medium/Low

[ASSUMPTIONS] What I'm assuming:
- [assumption 1] - Confidence: X%
- [assumption 2] - Confidence: X%

[INFORMATION_NEEDED] What would reduce uncertainty:
- [info 1] - How to get it: [method]
- [info 2] - How to get it: [method]

[DECISION_UNDER_UNCERTAINTY]
- Proceed with: [action]
- Because: [reason]
- Fallback if wrong: [plan B]
</uncertainty_analysis>
"""

ERROR_RECOVERY_PROMPT = """
When an error or unexpected result occurs:

<error_analysis>
[ERROR] What happened:
[description]

[EXPECTED] What should have happened:
[description]

[HYPOTHESIS] Why it failed (ranked by likelihood):
1. [cause] - X% likely
2. [cause] - Y% likely
3. [cause] - Z% likely

[INVESTIGATION]
- Check 1: [what to check]
- Check 2: [what to check]

[ROOT_CAUSE] (after investigation):
[actual cause]

[LESSON_LEARNED]:
[what to do differently next time]

[RECOVERY_ACTION]:
[next steps to recover]
</error_analysis>
"""


# =============================================================================
# PROMPT BUILDER CLASS
# =============================================================================


class ReasoningPromptBuilder:
    """
    Builds optimized reasoning prompts based on task and configuration.
    """

    def __init__(self, config: Optional[ReasoningPromptConfig] = None):
        self.config = config or ReasoningPromptConfig()

    def build_system_prompt(
        self, task_type: Optional[str] = None, include_self_critique: bool = True
    ) -> str:
        """
        Build complete system prompt for reasoning.

        Args:
            task_type: Optional specific task type
            include_self_critique: Whether to include self-critique section

        Returns:
            Complete system prompt
        """
        parts = [GPT_OSS_REASONING_SYSTEM]

        # Add task-specific section if applicable
        if task_type and task_type in TASK_SPECIFIC_PROMPTS:
            parts.append("\n" + TASK_SPECIFIC_PROMPTS[task_type])

        # Add self-critique if requested
        if include_self_critique:
            parts.append("\n" + SELF_CRITIQUE_PROMPT)

        return "\n".join(parts)

    def build_thinking_prompt(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        depth: Optional[ReasoningDepth] = None,
    ) -> str:
        """
        Build prompt to trigger thinking for a specific task.

        Args:
            task: The task to reason about
            context: Additional context
            depth: Reasoning depth level

        Returns:
            Prompt to trigger structured thinking
        """
        depth = depth or self.config.depth

        if depth == ReasoningDepth.QUICK:
            template = self._quick_thinking_template()
        elif depth == ReasoningDepth.STANDARD:
            template = self._standard_thinking_template()
        else:
            template = self._deep_thinking_template()

        prompt_parts = [
            f"Task: {task}",
            "",
            "Please reason through this using the following structure:",
            "",
            template,
        ]

        if context:
            # Format context nicely
            context_str = []
            for k, v in context.items():
                if k == "git_status" and v:
                    context_str.append(f"Git Status:\n{v}")
                elif k == "active_files" and v:
                    context_str.append(f"Active Files: {', '.join(v)}")
                else:
                    context_str.append(f"{k}: {v}")
            
            if context_str:
                prompt_parts.insert(1, "\nContext:\n" + "\n".join(context_str) + "\n")

        return "\n".join(prompt_parts)

    def _quick_thinking_template(self) -> str:
        return """<thinking>
[UNDERSTAND]
[DECISION]
[RISK]
</thinking>"""

    def _standard_thinking_template(self) -> str:
        return """<thinking>
[UNDERSTAND]
[CONTEXT]
[ASSUMPTIONS]
[OPTIONS]
[DECISION]
[RISK]
[CONFIDENCE]
</thinking>"""

    def _deep_thinking_template(self) -> str:
        return """<thinking>
=== PHASE 1: PERCEPTION ===
[OBSERVE]
[IMPLICIT]
[ENTITIES]

=== PHASE 2: COMPREHENSION ===
[CORE]
[CONTEXT]
[ASSUMPTIONS]
[CONSTRAINTS]
[SUCCESS_CRITERIA]

=== PHASE 3: ANALYSIS ===
[DECOMPOSE]
[DEPENDENCIES]
[OPTIONS]
[RISKS]

=== PHASE 4: REASONING ===
[HYPOTHESIS]
[EVIDENCE_FOR]
[EVIDENCE_AGAINST]
[COUNTER_ARGUMENTS]
[LOGICAL_CHAIN]

=== PHASE 5: DECISION ===
[DECISION]
[JUSTIFICATION]
[CONFIDENCE]
[FALLBACK]
[ACTION_ITEMS]
[EXPECTED_OUTCOME]

=== PHASE 6: VERIFICATION ===
[SAFETY_CHECK]
[VALIDATION]
[POTENTIAL_ISSUES]
[RISK_MITIGATION]
[FINAL_CONFIDENCE]
[READY]
</thinking>"""

    def build_refinement_prompt(self, original_reasoning: str, feedback: str, outcome: str) -> str:
        """
        Build prompt for refining reasoning based on feedback.

        Args:
            original_reasoning: The original thinking
            feedback: Feedback received
            outcome: What actually happened

        Returns:
            Prompt for reasoning refinement
        """
        return f"""Your previous reasoning led to an unexpected outcome. Please refine your thinking.

## Original Reasoning:
{original_reasoning}

## Feedback Received:
{feedback}

## Actual Outcome:
{outcome}

## Refinement Task:
Please analyze what went wrong and provide refined reasoning:

<error_analysis>
[ERROR] What happened vs expected
[ROOT_CAUSE] Why the original reasoning was flawed
[LESSON] What to learn from this
</error_analysis>

<refined_thinking>
[REVISED_UNDERSTANDING] Updated understanding based on new information
[REVISED_APPROACH] New approach accounting for what we learned
[REVISED_CONFIDENCE] Updated confidence with justification
[NEW_ACTION_ITEMS] Updated action items
</refined_thinking>
"""

    def get_task_type_from_message(self, message: str) -> Optional[str]:
        """
        Detect task type from user message.

        Args:
            message: User's message

        Returns:
            Detected task type or None
        """
        message_lower = message.lower()

        # Task type indicators
        indicators = {
            "code_generation": [
                "write",
                "create",
                "implement",
                "add function",
                "new feature",
                "generate code",
                "build",
            ],
            "debugging": [
                "fix",
                "bug",
                "error",
                "exception",
                "failing",
                "not working",
                "broken",
                "debug",
                "issue",
            ],
            "refactoring": [
                "refactor",
                "clean up",
                "reorganize",
                "restructure",
                "improve code",
                "optimize",
                "simplify",
            ],
            "security_review": [
                "security",
                "vulnerability",
                "audit",
                "penetration",
                "secure",
                "authentication",
                "authorization",
            ],
            "architecture_design": [
                "architecture",
                "design",
                "system design",
                "structure",
                "how should",
                "best approach",
                "planning",
            ],
        }

        for task_type, keywords in indicators.items():
            if any(kw in message_lower for kw in keywords):
                return task_type

        return None

    def determine_depth(self, message: str, estimated_complexity: float = 0.5) -> ReasoningDepth:
        """
        Determine appropriate reasoning depth.

        Args:
            message: User's message
            estimated_complexity: Complexity score 0-1

        Returns:
            Appropriate reasoning depth
        """
        message_lower = message.lower()

        # Quick indicators
        quick_indicators = ["show", "list", "what is", "read", "check", "status", "help", "how to"]

        # Deep indicators
        deep_indicators = [
            "refactor",
            "architecture",
            "design",
            "migration",
            "security audit",
            "optimize",
            "complex",
            "multiple files",
            "entire",
            "comprehensive",
            "thoroughly",
        ]

        if any(ind in message_lower for ind in quick_indicators):
            return ReasoningDepth.QUICK

        if any(ind in message_lower for ind in deep_indicators):
            return ReasoningDepth.DEEP

        if estimated_complexity > 0.7:
            return ReasoningDepth.DEEP
        elif estimated_complexity < 0.3:
            return ReasoningDepth.QUICK

        return ReasoningDepth.STANDARD


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_reasoning_system_prompt(task_type: Optional[str] = None) -> str:
    """Get the complete reasoning system prompt"""
    builder = ReasoningPromptBuilder()
    return builder.build_system_prompt(task_type=task_type)


def get_thinking_prompt(
    task: str,
    depth: ReasoningDepth = ReasoningDepth.STANDARD,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Get a thinking trigger prompt for a task"""
    builder = ReasoningPromptBuilder()
    return builder.build_thinking_prompt(task=task, context=context, depth=depth)


def detect_task_type(message: str) -> Optional[str]:
    """Detect task type from a message"""
    builder = ReasoningPromptBuilder()
    return builder.get_task_type_from_message(message)


def determine_reasoning_depth(message: str, complexity: float = 0.5) -> ReasoningDepth:
    """Determine appropriate reasoning depth for a message"""
    builder = ReasoningPromptBuilder()
    return builder.determine_depth(message, complexity)


# =============================================================================
# CLAUDE-STYLE 3-PHASE WORKFLOW PROMPTS
# =============================================================================

CLAUDE_WORKFLOW_PROMPTS = {
    "planning": """You are in PLANNING mode.

Your goal is to deeply understand the requirements and create a detailed implementation plan.

Steps:
1. Apply PERCEPTION phase thinking - understand what's being asked
2. Apply COMPREHENSION phase - understand the core problem and constraints
3. Apply ANALYSIS phase - break down the solution approach
4. Create implementation_plan.md with:
   - Problem context
   - Proposed changes (by component/file)
   - Verification strategy
   - Items requiring user review
5. Create task.md with concrete checklist
6. Request user approval before proceeding

Remember: Quality planning prevents execution issues.
""",
    "execution": """You are in EXECUTION mode.

Your goal is to implement the approved plan systematically and incrementally.

Steps:
1. Follow the approved implementation_plan.md
2. Apply DECISION phase thinking for each change
3. Make one logical change at a time
4. Test after significant modifications
5. Update task.md to track progress
6. Apply PRE-EXECUTION REVIEW before risky operations

Remember: Incremental progress with frequent testing.
""",
    "verification": """You are in VERIFICATION mode.

Your goal is to validate that all requirements are met and document your work.

Steps:
1. Apply VERIFICATION phase thinking
2. Run comprehensive tests (unit, integration, manual)
3. Validate edge cases
4. Check for regressions
5. Create walkthrough.md documenting:
   - What was modified
   - What was tested
   - Validation results
   - Proof of work (test output, screenshots)

Remember: Thorough verification builds confidence.
""",
}


def get_claude_workflow_prompt(phase: str) -> str:
    """
    Get Claude-style workflow prompt for a specific phase.

    Args:
        phase: One of 'planning', 'execution', 'verification'

    Returns:
        Workflow prompt for the specified phase
    """
    return CLAUDE_WORKFLOW_PROMPTS.get(phase, "")


# =============================================================================
# CLAUDE-STYLE REASONING PHASE PROMPTS (from YAML)
# =============================================================================


def get_claude_reasoning_phase(phase_name: str) -> str:
    """
    Get a specific Claude-style reasoning phase template.

    This loads from the YAML configuration if available, otherwise returns
    a default template.

    Args:
        phase_name: One of 'perception', 'comprehension', 'analysis',
                   'reasoning', 'change_impact', 'decision',
                   'pre_execution', 'verification'

    Returns:
        Reasoning phase template
    """
    try:
        from .prompts import get_prompts_config

        config = get_prompts_config()
        phases = config._prompts_data.get("claude_reasoning_phases", {})
        return phases.get(phase_name, f"[PHASE: {phase_name.upper()}]\n")
    except Exception:
        # Fallback to basic template if config not available
        return f"[PHASE: {phase_name.upper()}]\n"


def get_claude_example(example_name: str) -> str:
    """
    Get a Claude-style interaction example.

    Args:
        example_name: Example identifier (e.g., 'simple_fix', 'complex_feature')

    Returns:
        Example interaction text
    """
    try:
        from .prompts import get_prompts_config

        config = get_prompts_config()
        examples = config._prompts_data.get("claude_examples", {})
        return examples.get(example_name, "")
    except Exception:
        return ""


# =============================================================================
# CLAUDE INTEGRATION HELPERS
# =============================================================================


class ClaudeReasoningBuilder:
    """Helper class for building Claude-style reasoning prompts."""

    @staticmethod
    def build_phase_prompt(
        phase_name: str, task_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build a complete prompt for a specific reasoning phase.

        Args:
            phase_name: Name of the reasoning phase
            task_context: Optional context dictionary

        Returns:
            Complete phase prompt with context
        """
        phase_template = get_claude_reasoning_phase(phase_name)

        if task_context:
            context_str = "\n".join(
                f"{k}: {v}" for k, v in task_context.items() if v
            )
            return f"{phase_template}\n\nContext:\n{context_str}"

        return phase_template

    @staticmethod
    def build_workflow_transition(
        from_phase: str, to_phase: str, reason: str = ""
    ) -> str:
        """
        Build a prompt for transitioning between workflow phases.

        Args:
            from_phase: Current phase
            to_phase: Target phase
            reason: Optional reason for transition

        Returns:
            Transition prompt
        """
        transition = f"\n--- Transitioning from {from_phase.upper()} to {to_phase.upper()} ---\n"
        if reason:
            transition += f"\nReason: {reason}\n"
        transition += f"\n{get_claude_workflow_prompt(to_phase)}"
        return transition

    @staticmethod
    def validate_reasoning_output(output: str) -> Dict[str, bool]:
        """
        Validate that reasoning output contains expected phase markers.

        Args:
            output: Agent's reasoning output

        Returns:
            Dictionary mapping phase names to presence (True/False)
        """
        phases = [
            "PERCEPTION",
            "COMPREHENSION",
            "ANALYSIS",
            "REASONING",
            "CHANGE IMPACT",
            "DECISION",
            "PRE-EXECUTION",
            "VERIFICATION",
        ]

        validation = {}
        for phase in phases:
            validation[phase] = f"[PHASE" in output and phase in output.upper()

        return validation

