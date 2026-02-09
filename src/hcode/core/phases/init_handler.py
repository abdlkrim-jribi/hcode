"""
Init handler for codebase analysis.

Responsible for:
- Loading init analysis prompt
- Executing agent-driven codebase exploration using tools
- Validating hcode.md generation
- Providing structured results
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from hcode.core.protocols import AgentContext
from hcode.core.phases.base_handler import BasePhaseHandler

logger = logging.getLogger(__name__)


@dataclass
class InitResult:
    """Result of init analysis."""
    success: bool
    hcode_path: Optional[Path] = None
    tool_results: List[Dict[str, Any]] = None
    response_text: str = ""
    error: Optional[str] = None

    def __post_init__(self):
        if self.tool_results is None:
            self.tool_results = []


class InitHandler(BasePhaseHandler):
    """
    Handler for /init command - agent-driven codebase analysis.

    Extends BasePhaseHandler to leverage common functionality like tool
    execution, response parsing, and display utilities.

    Uses the agent's tools (Glob, Read, Grep) to intelligently explore
    the codebase and generate comprehensive hcode.md documentation.
    """

    def __init__(
        self,
        provider: Any,
        tool_executor: Any,
        context_manager: Any = None,
        console: Any = None,
    ):
        """
        Initialize init handler.

        Args:
            provider: AI provider for generating responses
            tool_executor: Executor for tool calls
            context_manager: Context manager (optional)
            console: Rich console for output (optional)
        """
        # Initialize base handler (no artifact_manager needed for init)
        super().__init__(
            artifact_manager=None,
            provider=provider,
            tool_executor=tool_executor,
            context_manager=context_manager,
        )

        self.phase_name = "init"
        self.console = console

        # Initialize HcodeDisplay for modern UI
        self._hcode_display = None
        if console:
            try:
                from hcode.ui.hcode_display import get_hcode_display
                self._hcode_display = get_hcode_display(console)
            except ImportError:
                pass
    
    # ──────────────────────────────────────────────────────────
    # Static helper – JSON string unescape that is safe for UTF-8
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def _unescape_json_str(s: str) -> str:
        """
        Unescape a JSON string value extracted via regex.

        Handles ``\\n``, ``\\t``, ``\\r``, ``\\"``, ``\\/``, ``\\\\``,
        and ``\\uXXXX`` without corrupting multi-byte UTF-8 characters.
        (The ``unicode_escape`` codec must never be used here – it
        reinterprets every byte as a Latin-1 code-point, destroying
        any non-ASCII content.)
        """
        import re as _re

        s = s.replace('\\\\', '\x00')          # placeholder for literal backslash
        s = s.replace('\\n', '\n')
        s = s.replace('\\t', '\t')
        s = s.replace('\\r', '\r')
        s = s.replace('\\"', '"')
        s = s.replace('\\/', '/')
        s = s.replace('\\b', '\b')
        s = s.replace('\\f', '\f')

        def _uni(m):
            return chr(int(m.group(1), 16))

        s = _re.sub(r'\\u([0-9a-fA-F]{4})', _uni, s)
        s = s.replace('\x00', '\\')            # restore backslashes
        return s

    # ──────────────────────────────────────────────────────────
    # Deep programmatic codebase exploration
    # ──────────────────────────────────────────────────────────
    def _programmatic_explore(self, context: AgentContext) -> str:
        """
        Deep programmatic exploration of the codebase.

        Extracts directory tree, package config, README, entry-point
        source, file inventory, test infrastructure, and common code
        patterns — all *without* AI tool calls.  The AI then uses this
        as its starting map and focuses its rounds on understanding
        behaviour and architecture rather than re-discovering structure.
        """
        import re as _re

        working_dir = Path(context.working_dir)
        _EXCLUDE = {
            '.git', '.venv', 'node_modules', '__pycache__', '.idea',
            '.mypy_cache', '.pytest_cache', '.tox', '.ruff_cache',
        }

        def _should_exclude(p: Path) -> bool:
            return any(ex in p.parts for ex in _EXCLUDE)

        def _read_safe(path: Path, max_lines: int = 80) -> str:
            """Read file with a line cap; safe against encoding issues."""
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                shown = lines[:max_lines]
                out = ''.join(shown)
                if len(lines) > max_lines:
                    out += f"\n[... {len(lines) - max_lines} more lines]\n"
                return out
            except Exception:
                return "(unreadable)\n"

        parts: List[str] = []

        # ── 1. Directory tree (Recursive up to depth 4) ──────────
        tree_lines: List[str] = []
        
        def _list_tree(path: Path, prefix: str = "", current_depth: int = 0, max_depth: int = 4):
            if current_depth >= max_depth:
                return
                
            try:
                # Sort: Directories first, then files
                items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                
                for i, item in enumerate(items):
                    name = item.name
                    
                    # Skip excluded items
                    if name in _EXCLUDE or (name.startswith('.') and name not in ('.env.example', '.hcode', '.hcoderc')):
                        continue
                        
                    is_last = (i == len(items) - 1)
                    # Visual branch characters could be used, but simple indentation is token-efficient
                    # using 2 spaces per level
                    indent = "  " * current_depth
                    
                    if item.is_dir():
                        tree_lines.append(f"{indent}{name}/")
                        _list_tree(item, prefix, current_depth + 1, max_depth)
                    else:
                        tree_lines.append(f"{indent}{name}")
                        
            except OSError:
                tree_lines.append(f"{prefix}  (access denied)")

        try:
            _list_tree(working_dir)
        except Exception as e:
            tree_lines.append(f"(Error listing tree: {e})")
            
        parts.append("### Directory Structure\n" + "\n".join(tree_lines))

        # ── 2. Package definition (first one found) ─────────────
        for pkg_name in ('pyproject.toml', 'package.json', 'setup.py', 'setup.cfg'):
            pkg_path = working_dir / pkg_name
            if pkg_path.exists():
                parts.append(f"### {pkg_name}\n```\n{_read_safe(pkg_path, 100)}```")
                break

        # ── 3. README ────────────────────────────────────────────
        for readme_name in ('README.md', 'README.rst', 'readme.md'):
            readme_path = working_dir / readme_name
            if readme_path.exists():
                parts.append(f"### {readme_name}\n{_read_safe(readme_path, 50)}")
                break

        # ── 4. Config / env files ────────────────────────────────
        cfg_snippets: List[str] = []
        for cfg_name in ('.env.example', '.env.sample', '.hcoderc'):
            cfg_path = working_dir / cfg_name
            if cfg_path.exists():
                cfg_snippets.append(f"[{cfg_name}]:\n{_read_safe(cfg_path, 25)}")
        if cfg_snippets:
            parts.append("### Config / Environment\n" + "\n".join(cfg_snippets))

        # ── 5. Source file inventory ─────────────────────────────
        all_files: List[Path] = []
        ext_counts: Dict[str, int] = {}
        for f in sorted(working_dir.rglob("*")):
            if not f.is_file() or _should_exclude(f) or f.name.startswith('.'):
                continue
            ext = f.suffix.lower() or '(none)'
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
            all_files.append(f)
        inv_lines = [f"Total: {len(all_files)} files"]
        for ext, cnt in sorted(ext_counts.items(), key=lambda x: -x[1])[:12]:
            inv_lines.append(f"  {ext}: {cnt}")
        parts.append("### File Inventory\n" + "\n".join(inv_lines))

        # ── 6. Entry points (with source content) ───────────────
        entry_names = {
            '__main__.py', 'main.py', 'app.py', 'index.js', 'index.ts',
            'server.py', 'manage.py', 'main_cli.py',
        }
        entries_found = [f for f in all_files if f.name in entry_names]
        if entries_found:
            entry_parts: List[str] = []
            for ef in entries_found[:3]:
                rel = ef.relative_to(working_dir)
                entry_parts.append(f"[{rel}]:\n{_read_safe(ef, 50)}")
            parts.append("### Entry Points (source)\n" + "\n".join(entry_parts))

        # ── 6b. Core source files (read actual logic, not just entry points) ─
        # Pick the largest / most central .py files that are NOT entry points
        # or __init__.py.  These give the AI real code to anchor analysis on.
        _SKIP_NAMES = set(entry_names) | {'__init__.py', 'conftest.py', 'setup.py'}
        core_candidates = [
            f for f in all_files
            if f.suffix == '.py'
            and f.name not in _SKIP_NAMES
            and 'test' not in f.name.lower()
            and not _should_exclude(f)
        ]
        # Sort by file size descending — bigger files tend to be the real logic
        core_candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
        if core_candidates:
            core_parts: List[str] = []
            for cf in core_candidates[:3]:  # top-3 by size
                rel = cf.relative_to(working_dir)
                core_parts.append(f"[{rel}] ({cf.stat().st_size} bytes):\n{_read_safe(cf, 60)}")
            parts.append("### Core Source Files (largest modules)\n" + "\n".join(core_parts))

        # ── 7. Main package submodule listing ────────────────────
        for base in (working_dir / "src", working_dir):
            if not base.is_dir():
                continue
            for pkg in sorted(base.iterdir()):
                if (
                    not pkg.is_dir()
                    or pkg.name.startswith('.')
                    or pkg.name in _EXCLUDE
                ):
                    continue
                init_py = pkg / '__init__.py'
                if not init_py.exists():
                    continue
                # Read __init__.py only if it has real content
                if init_py.stat().st_size > 100:
                    rel = init_py.relative_to(working_dir)
                    parts.append(f"### {rel}\n{_read_safe(init_py, 40)}")
                # List direct submodules
                subs: List[str] = []
                for sub in sorted(pkg.iterdir()):
                    if sub.name.startswith('.') or sub.name in _EXCLUDE:
                        continue
                    subs.append(f"  {sub.name}{'/' if sub.is_dir() else ''}")
                if subs:
                    parts.append(
                        f"### {pkg.name}/ submodules\n" + "\n".join(subs)
                    )
                break  # first package only
            break  # src/ checked first, then root

        # ── 8. Test infrastructure ───────────────────────────────
        test_root = None
        for td in ('tests', 'test', '__tests__'):
            tp = working_dir / td
            if tp.is_dir():
                test_root = tp
                break
        if test_root:
            test_files = [
                str(f.relative_to(working_dir))
                for f in test_root.rglob("*")
                if f.is_file() and not _should_exclude(f)
            ]
            parts.append(
                f"### Tests ({len(test_files)} files)\n"
                + "\n".join(f"  {tf}" for tf in test_files[:20])
            )
            # Read one sample test file for conventions
            sample_tests = sorted(
                (f for f in test_root.rglob("test_*.py") if not _should_exclude(f)),
                key=lambda p: p.name,
            )
            if sample_tests:
                rel = sample_tests[0].relative_to(working_dir)
                parts.append(
                    f"### Sample Test ({rel})\n{_read_safe(sample_tests[0], 40)}"
                )

        # ── 9. Code-pattern scan (grep-style, no AI) ────────────
        py_files = [f for f in all_files if f.suffix == '.py']
        patterns_to_find = {
            'Classes':     _re.compile(r'^\s*class\s+(\w+)'),
            'Async defs':  _re.compile(r'^\s*async\s+def\s+(\w+)'),
            'Public defs': _re.compile(r'^def\s+(\w+)'),
            'Decorators':  _re.compile(r'^\s*(@\w[\w.]*)'),
        }
        findings: Dict[str, List[str]] = {k: [] for k in patterns_to_find}
        for f in py_files[:60]:  # cap to keep scan fast
            try:
                rel = str(f.relative_to(working_dir))
                with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                    for i, line in enumerate(fh, 1):
                        for name, pat in patterns_to_find.items():
                            if pat.search(line) and len(findings[name]) < 20:
                                findings[name].append(
                                    f"  {rel}:{i}: {line.strip()[:90]}"
                                )
            except Exception:
                continue
        pat_lines: List[str] = []
        for name, matches in findings.items():
            if matches:
                pat_lines.append(f"[{name}] ({len(matches)} found):")
                pat_lines.extend(matches[:12])
        if pat_lines:
            parts.append("### Code Patterns\n" + "\n".join(pat_lines))

        return "\n\n".join(parts)

    async def analyze(self, context: AgentContext) -> InitResult:
        """
        Execute codebase analysis.
        
        Steps:
        1. Load init analysis prompt
        2. Build system prompt with identity + tool format
        3. Execute agent with tools using _generate_and_execute
        4. Validate hcode.md was created
        5. Return structured result
        
        Args:
            context: Current agent context
            prompt: The initial prompt for the agent.
            
        Returns:
            InitResult with success status and metadata
        """
        try:
            # Cleanup existing hcode.md to ensure fresh analysis
            hcode_path = Path(context.working_dir) / ".hcode" / "hcode.md"
            if hcode_path.exists():
                try:
                    hcode_path.unlink()
                    logger.info("Removed existing hcode.md for fresh initialization")
                except Exception as e:
                    logger.warning(f"Failed to remove existing hcode.md: {e}")

            # Notify user
            # self._display_banner() # Method not available
            self._display("\n🚀 Initializing codebase analysis...\n", style="info")
            
            # Load prompt and inject pre-explored codebase snapshot
            prompt = self._load_init_prompt()
            exploration_data = self._programmatic_explore(context)
            prompt = prompt.replace("{{CODEBASE_SNAPSHOT}}", exploration_data)
            system_prompt = self._get_init_system_prompt(context)
            
            self._display("🤖 Agent starting deep codebase analysis...", style="info")
            
            # Start thinking display
            if self._hcode_display:
                self._hcode_display.start_thinking()
            
            # Execute agent with tools
            response_text, tool_results = await self._generate_and_execute(
                prompt=prompt,
                context=context,
                system_prompt=system_prompt,
                max_rounds=24,  # 12 deep reading + 8 synthesis + 4 write/buffer
            )
            
            # End thinking display
            if self._hcode_display:
                self._hcode_display.end_thinking()
            
            # Validate hcode.md was created
            hcode_path = Path(context.working_dir) / ".hcode" / "hcode.md"
            
            if hcode_path.exists():
                self._display(f"✨ Generated: {hcode_path}", style="success")
                return InitResult(
                    success=True,
                    hcode_path=hcode_path,
                    tool_results=tool_results,
                    response_text=response_text,
                )
            else:
                # Agent completed but didn't create hcode.md
                return InitResult(
                    success=False,
                    error="Agent completed analysis but hcode.md was not created",
                    tool_results=tool_results,
                    response_text=response_text,
                )
                
        except Exception as e:
            logger.exception(f"Init analysis failed: {e}")
            return InitResult(
                success=False,
                error=str(e),
            )
    
    def _load_init_prompt(self) -> str:
        """
        Load init analysis prompt from core_prompts.
        
        Returns:
            Prompt content
        """
        # Try to load from core_prompts
        try:
            # init_handler.py is in src/hcode/core/phases/
            # We need to go up 3 levels to get to src/hcode/, then into config/
            prompt_path = Path(__file__).parent.parent.parent / "config" / "core_prompts" / "core" / "init_analysis_prompt.md"
            
            logger.info(f"[init] Loading prompt from: {prompt_path}")
            logger.info(f"[init] Prompt exists: {prompt_path.exists()}")
            
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"[init] Successfully loaded prompt ({len(content)} chars)")
                    return content
            else:
                logger.warning(f"[init] Prompt file not found at: {prompt_path}")
        except Exception as e:
            logger.warning(f"Failed to load init_analysis_prompt.md: {e}")
        
        # Fallback inline prompt
        return """# Codebase Initialization Analysis

You are performing comprehensive codebase analysis for /init. Use your tools (Glob, Read, Grep) to explore this codebase and generate a detailed hcode.md file in .hcode/ directory.

## Analysis Phases:

1. **Project Identification**: Use Glob to find package files, Read them to extract name, languages, frameworks
2. **Architecture**: Use Glob for structure, Read entry points, Grep for patterns (routes, models, services)
3. **Code Quality**: Find tests with Glob, identify frameworks, locate CI/CD configs
4. **Components**: Use Grep to find models, API endpoints, auth patterns. Map core business logic
5. **Developer Experience**: Read README, find env configs, document setup

## Generate .hcode/hcode.md

Create comprehensive documentation with:
- Project Overview (name, type, languages, frameworks)
- Architecture Summary (patterns, directory layout, entry points)
- Dependencies (production and dev with purposes)
- Core Components Map (locations, purposes, relationships)
- Data Layer (models, database config)
- API Surface (endpoints with handlers)
- Configuration (env vars, config files)
- Testing (framework, locations, patterns)
- Code Patterns (naming, style, design patterns observed)
- Implementation Guidelines (specific, actionable advice)

Be thorough, use tools effectively, and provide specific paths and examples."""
    
    def _get_init_system_prompt(self, context: AgentContext) -> str:
        """
        Build system prompt for init analysis.
        
        Includes identity, tool format, and init-specific instructions.
        
        Args:
            context: Current agent context
            
        Returns:
            Complete system prompt
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()
            
            # Get identity and tool format
            identity = loader.get_identity()
            tool_format = loader.get_tool_format()
            
            system_base = f"""{identity}

{tool_format}"""
            
        except Exception as e:
            logger.warning(f"Failed to load core prompts: {e}")
            system_base = "You are Hcode, an AI coding assistant."
        
    
        # Add init-specific instructions (GPT OSS 120B optimized)
        init_instructions = f"""

## INIT MODE: 4-Dimension Deep Analysis Protocol

Working directory: {context.working_dir}

### Reasoning Protocol (GPT OSS 120B)

Use <thinking> tags for ALL internal reasoning:

<thinking>
Step 1: [Action] — [Reasoning for this step]
Step 2: [Action] — [Reasoning for this step]
...
Therefore: [Conclusion leading to next action]
</thinking>

**Key principles:**
- Keep each thought LINEAR — no nested reasoning
- Use "Therefore..." transitions between reasoning and conclusions
- Use analytical reasoning; prioritize precision over novelty
- Validate each step before proceeding

### 4-Dimension Phase Structure (24 rounds total)

**Dimension A (Rounds 1-6): ARCHITECTURAL PATTERNS**
- Read core domain files, entry points, abstractions
- Identify: layering, design patterns, module boundaries
- After each Read: summarize what you learned and WHY it matters

**Dimension B (Rounds 7-10): DEPENDENCY GRAPH**
- Map imports, data flow, coupling between modules
- Identify: circular dependencies, external integrations
- Use Grep to find import patterns across the codebase

**Dimension C (Rounds 11-16): CODE QUALITY BASELINE**
- Read the most complex test file, error handling patterns
- Assess: test coverage, complexity, documentation quality
- Identify: fragile zones, hot spots

**Dimension D (Rounds 17-20): CONTEXT EXTRACTION**
- Trace a complete request path: Input → Processing → Output
- Extract: naming conventions, import patterns, code philosophy
- Verify hypotheses from earlier dimensions

**Generation (Round 21+): WRITE .hcode/hcode.md**
- You MUST use the Write tool in JSON format
- DO NOT output markdown text directly — it will not be saved

### CRITICAL: Output Format

**WRONG** (will fail):
```markdown
# Project Name
...
```

**CORRECT** (required):
```json
{{"tool": "Write", "arguments": {{"TargetFile": ".hcode/hcode.md", "CodeContent": "# Project Name\\n..."}}}}
```

### File Path Verification Protocol

BEFORE reading any file, verify it exists using Glob or LS.
NEVER assume paths. If Read fails with "File not found", you violated this protocol.

### Evidence Citations

Use `[Evidence: file.py:line_num]` format for key architectural claims.
Every finding in hcode.md should trace back to a specific file read.

**BEGIN DIMENSION A — Read the most logically complex file in the snapshot.**
"""
    
        return system_base + init_instructions
    
    def _get_current_phase(self, round_num: int) -> str:
        """Determine current dimension based on round number."""
        if round_num < 6:
            return "DIM_A_ARCHITECTURE"
        elif round_num < 10:
            return "DIM_B_DEPENDENCIES"
        elif round_num < 16:
            return "DIM_C_QUALITY"
        elif round_num < 20:
            return "DIM_D_CONTEXT"
        else:
            return "GENERATION"

    def _get_phase_message(self, round_num: int) -> str:
        """Get dimension-specific guidance message."""
        phase = self._get_current_phase(round_num)

        if phase == "DIM_A_ARCHITECTURE":
            remaining = 6 - round_num
            return f"**Dimension A: Architectural Patterns** (Round {round_num + 1}/6) — {remaining} rounds for architecture analysis"
        elif phase == "DIM_B_DEPENDENCIES":
            remaining = 10 - round_num
            return f"**Dimension B: Dependency Graph** (Round {round_num + 1}/10) — {remaining} rounds for dependency mapping"
        elif phase == "DIM_C_QUALITY":
            remaining = 16 - round_num
            return f"**Dimension C: Code Quality** (Round {round_num + 1}/16) — {remaining} rounds for quality assessment"
        elif phase == "DIM_D_CONTEXT":
            remaining = 20 - round_num
            return f"**Dimension D: Context Extraction** (Round {round_num + 1}/20) — {remaining} rounds to extract conventions"
        else:
            return f"**Generation Phase** (Round {round_num + 1}) — OUTPUT Write tool JSON for .hcode/hcode.md NOW"
    
    
    async def _generate_and_execute(
        self,
        prompt: str,
        context: AgentContext,
        system_prompt: Optional[str] = None,
        max_rounds: int = 10,
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Generate response and execute tool calls (multi-turn loop).
        
        This follows the BasePhaseHandler pattern for tool execution.
        
        Args:
            prompt: User prompt
            context: Current agent context
            system_prompt: System prompt
            max_rounds: Maximum rounds
            
        Returns:
            Tuple of (response_text, tool_results)
        """
        from hcode.providers.base import Message
        import re
        import json
        
        all_tool_results = []
        synthesis_buffer = []
        last_response = ""
        
        # Start analysis loop
        for round_num in range(max_rounds):
            logger.info(f"[init] Generation round {round_num + 1}/{max_rounds}...")

            # Build initial messages for the first round, or continue with history
            if round_num == 0:
                messages = [Message(role="user", content=prompt)]

            try:
                # Call provider
                response = await self.provider.generate_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=16384,
                )

                # Extract content
                if hasattr(response, 'content'):
                    last_response = response.content
                elif isinstance(response, dict):
                    last_response = response.get('content', '')
                else:
                    last_response = str(response)

            except Exception as e:
                logger.error(f"Provider call failed: {e}")
                self._display(f"Generation error: {e}", style="error")
                break

            # Display response text (excluding tool calls)
            text_portion = self._extract_text_response(last_response)
            if text_portion and len(text_portion.strip()) > 20:
                self._display(text_portion, style="default")

            # ── Extract and execute tool calls (primary path) ──
            tool_calls = self._extract_tool_calls(last_response)
            logger.info(f"[init] Extracted {len(tool_calls)} tool calls")

            if not tool_calls:
                # No tool calls.
                hcode_path = Path(context.working_dir) / ".hcode" / "hcode.md"
                
                # Check for direct markdown generation in generation phase (Round 20+)
                if round_num >= 20 and self._looks_like_markdown_content(last_response):
                    logger.info("[init] Round 20+ no tool calls but markdown detected — fallback extraction")
                    extracted = self._extract_hcode_from_text(last_response)
                    if extracted:
                        try:
                            hcode_path.parent.mkdir(parents=True, exist_ok=True)
                            hcode_path.write_text(extracted, encoding="utf-8")
                            self._display("\n📝 Extracted hcode.md from response text", style="success")
                            logger.info("[init] Saved hcode.md via fallback extraction")
                            break
                        except Exception as write_err:
                            logger.error(f"Failed to save extracted hcode.md: {write_err}")
                
                # Valid text output handling
                phase = self._get_current_phase(round_num)

                # Dimensions A-C: Text output without tools is a protocol violation
                if round_num < 16 and phase in ("DIM_A_ARCHITECTURE", "DIM_B_DEPENDENCIES", "DIM_C_QUALITY"):
                    logger.warning(f"[init] Round {round_num + 1}: Agent output text instead of exploring ({phase})")
                    dim_name = phase.replace("DIM_", "Dimension ").replace("_", ": ", 1).replace("_", " ")
                    reminder_msg = f"""
**PROTOCOL VIOLATION** — You are in **{dim_name}** (Round {round_num + 1}).

You MUST use tools to explore the codebase:
- Use `Read` to understand code (primary)
- Use `Glob` to find files
- Use `Grep` to find patterns

Use <thinking> tags to reason about what to read next, then call the tool.
DO NOT write documentation yet.
"""
                    messages.append(Message(role="assistant", content=last_response))
                    messages.append(Message(role="user", content=reminder_msg))
                    continue

                # Dimension D: Text output is valid synthesis -> BUFFER & CONTINUE
                elif round_num < 20 and phase == "DIM_D_CONTEXT":
                    logger.info(f"[init] Round {round_num + 1}: Context extraction step recorded")

                    # Capture synthesis content
                    synthesis_buffer.append(f"## Context Extraction (Round {round_num+1})\n\n{last_response}")

                    remaining = 20 - round_num
                    reminder_msg = f"""
**Context Extraction Captured** (Round {round_num + 1}/20)

Your synthesis has been recorded. {remaining} rounds remain before generation.

Continue extracting conventions, tracing request paths, and verifying hypotheses.
Use <thinking> tags to reason, then take action or continue synthesis.
"""
                    messages.append(Message(role="assistant", content=last_response))
                    messages.append(Message(role="user", content=reminder_msg))
                    continue
                
                # PHASE 3 (Round 20+): Text output without Write tool -> ERROR & RETRY (Do not break!)
                elif round_num >= 20:
                    logger.warning(f"[init] Round {round_num + 1}: Text output in generation phase (Missing Write Tool)")
                    reminder_msg = """
🚨 **GENERATION ERROR**

You output text but failed to use the `Write` tool.
You are in **Phase 3: Generation**.

**You MUST use the `Write` tool to create `.hcode/hcode.md`.**
Output the JSON tool call now.
"""
                    messages.append(Message(role="assistant", content=last_response))
                    messages.append(Message(role="user", content=reminder_msg))
                    continue
                
                # Should not reach here if logic is correct, but safe break
                break

            # Execute tools
            tool_results = await self._execute_tools(tool_calls, context)
            all_tool_results.extend(tool_results)

            # Add assistant response to message history
            messages.append(Message(role="assistant", content=last_response))

            # Check if hcode.md was created by Write tool (primary success)
            hcode_path = Path(context.working_dir) / ".hcode" / "hcode.md"
            if hcode_path.exists():
                logger.info("[init] hcode.md created via Write tool — analysis complete!")
                break

            # ── Feed results back with phase-aware reminder ────
            phase_msg = self._get_phase_message(round_num)
            results_feedback = self._format_tool_results_enhanced(tool_results, context)

            # Check if Write tool was called
            write_tool_called = any(tc.get("tool", "").lower() in ["write", "writetool"] for tc in tool_calls)

            # Build reminder based on dimension transitions
            reminder = ""
            if round_num == 5:
                reminder = "\n\nTransition: **Dimension B — Dependency Graph.** Map imports, data flow, and coupling between modules."
            elif round_num == 9:
                reminder = "\n\nTransition: **Dimension C — Code Quality.** Read tests, error handling, assess quality baseline."
            elif round_num == 15:
                reminder = "\n\nTransition: **Dimension D — Context Extraction.** Trace request paths, extract conventions, verify hypotheses."
            elif round_num == 19:
                reminder = "\n\nTransition: **Generation Phase.** Output Write tool JSON for .hcode/hcode.md in your next response."
            elif round_num >= 20 and not write_tool_called:
                reminder = """

**GENERATION PHASE — WRITE .hcode/hcode.md NOW**

Use the Write tool in JSON format:
```json
{"tool": "Write", "arguments": {"TargetFile": ".hcode/hcode.md", "CodeContent": "# Project Name\\n..."}}
```
"""

            messages.append(Message(
                role="user",
                content=f"{phase_msg}\n\nTool execution results:\n\n{results_feedback}{reminder}\n\nContinue your analysis or write hcode.md."
            ))

        # CRITICAL: If max rounds reached and no hcode.md, force a final reminder
        # Validate hcode.md was created
        hcode_path = Path(context.working_dir) / ".hcode" / "hcode.md"

        # FALLBACK: If file doesn't exist, try to extract it from the agent's text output
        if not hcode_path.exists():
             logger.info("[init] hcode.md not found via tool. Attempting fallback...")
             
             # 1. Try extracting from last response
             extracted_content = self._extract_hcode_from_text(last_response)
             
             # 2. If that failed, check if we have a synthesis buffer
             if not extracted_content and synthesis_buffer:
                 logger.info(f"[init] Using {len(synthesis_buffer)} buffered synthesis blocks as fallback")
                 extracted_content = "# Hcode Analysis (Synthesized)\n\n" + "\n\n".join(synthesis_buffer)
                 
             if not extracted_content and len(messages) > 1:
                 # 3. Check the last assistant message in history
                 last_assistant_msg = next((m.content for m in reversed(messages) if m.role == "assistant"), "")
                 extracted_content = self._extract_hcode_from_text(last_assistant_msg)

             if extracted_content:
                 try:
                     hcode_path.parent.mkdir(parents=True, exist_ok=True)
                     hcode_path.write_text(extracted_content, encoding="utf-8")
                     self._display(f"📝 Recovered hcode.md from analysis text", style="info")
                 except Exception as e:
                     logger.error(f"Failed to save extracted hcode content: {e}")

        if not hcode_path.exists():
            logger.warning("[init] Max rounds reached without hcode.md creation - sending final demand")

            # Send one final CRITICAL message with EXPLICIT Write tool example
            final_demand = f"""
⚠️⚠️⚠️ CRITICAL FAILURE ⚠️⚠️⚠️

You have completed {max_rounds} rounds of analysis but have NOT created .hcode/hcode.md!

THIS IS YOUR FINAL CHANCE. YOU MUST NOW OUTPUT A WRITE TOOL CALL.

Do NOT write any more text. Do NOT think. ONLY output this JSON tool call:

```json
{{"tool": "Write", "arguments": {{"TargetFile": ".hcode/hcode.md", "CodeContent": "# Project Name\\n\\n## Overview\\n[What you learned]\\n\\n## Tech Stack\\n[Languages and frameworks]\\n\\n## Structure\\n[Key directories]\\n\\n## Key Files\\n[Important files discovered]"}}}}
```

Replace the placeholder content with ALL information you gathered about this codebase.

DO IT NOW!"""

            messages.append(Message(
                role="user",
                content=final_demand
            ))

            # Give agent ONE more chance
            try:
                response = await self.provider.generate_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=16384,
                )

                if hasattr(response, 'content'):
                    last_response = response.content
                elif isinstance(response, dict):
                    last_response = response.get('content', '')
                else:
                    last_response = str(response)

                # Try tool calls first
                tool_calls = self._extract_tool_calls(last_response)
                if tool_calls:
                    tool_results = await self._execute_tools(tool_calls, context)
                    all_tool_results.extend(tool_results)

                # Check if file exists now
                if not hcode_path.exists():
                    # LAST RESORT: Extract from final response
                    extracted_final = self._extract_hcode_from_text(last_response)
                    if extracted_final:
                         hcode_path.parent.mkdir(parents=True, exist_ok=True)
                         hcode_path.write_text(extracted_final, encoding="utf-8")
                         self._display(f"📝 Recovered hcode.md from final demand", style="info")

            except Exception as e:
                logger.error(f"Final Write attempt failed: {e}")

        return last_response, all_tool_results

    def _looks_like_markdown_content(self, text: str) -> bool:
        """
        Check if text is structured markdown documentation suitable for
        hcode.md extraction.

        Requires a title header AND at least two section headers.
        Explicitly rejects text that looks like a JSON tool call — those
        must go through the proper JSON-parsing path instead.
        """
        if not text or len(text.strip()) < 200:
            return False

        # Reject tool-call responses — they are handled by JSON parsing
        if '"tool"' in text and '"arguments"' in text:
            return False

        # Must have a title (# …) and at least 2 section headers (## …)
        has_title = text.startswith('# ') or '\n# ' in text
        h2_count = text.count('\n## ')

        return has_title and h2_count >= 2
    
    def _extract_hcode_from_text(self, text: str) -> Optional[str]:
        """
        Extract hcode.md content from a raw text response.

        Priority order:
        1. Brace-balanced JSON parse of a Write tool call  →  uses
           ``json.loads`` which handles all escapes correctly.
        2. Quote-aware regex on a malformed JSON block  →  uses
           ``_unescape_json_str`` (never ``unicode_escape``).
        3. Content inside a markdown code block (````markdown …```)
        4. Raw markdown in the response body (title + ≥2 ## headers)
        """
        import re
        import json

        if not text:
            return None

        # ── 1 & 2: JSON Write-tool call (well-formed or malformed) ─
        if '"CodeContent"' in text:
            # Brace-balanced extraction handles nested JSON correctly
            start = text.find('{')
            if start != -1:
                depth, in_str, escaped, end = 0, False, False, -1
                for i in range(start, len(text)):
                    c = text[i]
                    if escaped:
                        escaped = False
                        continue
                    if c == '\\' and in_str:
                        escaped = True
                        continue
                    if c == '"':
                        in_str = not in_str
                    elif not in_str:
                        if c == '{':
                            depth += 1
                        elif c == '}':
                            depth -= 1
                            if depth == 0:
                                end = i
                                break
                if end > start:
                    try:
                        # Path 1: proper json.loads (handles \n, \uXXXX etc)
                        parsed = json.loads(text[start:end + 1])
                        content = (
                            parsed.get("arguments", {}).get("CodeContent")
                            or parsed.get("CodeContent")
                        )
                        if content and len(content) > 100 and "## " in content:
                            logger.info("[init] Extracted CodeContent via json.loads")
                            return content
                    except json.JSONDecodeError:
                        # Path 2: JSON is broken — regex + safe unescape
                        m = re.search(
                            r'"CodeContent"\s*:\s*"((?:[^"\\]|\\.)*)"', text
                        )
                        if m:
                            content = self._unescape_json_str(m.group(1))
                            if content and len(content) > 100 and "## " in content:
                                logger.info("[init] Extracted CodeContent via lenient regex")
                                return content

        # ── 3: Content inside a markdown code block ──────────────
        code_block_match = re.search(
            r'```(?:markdown)?\s*\n(# .+?)\n```', text, re.DOTALL
        )
        if code_block_match:
            content = code_block_match.group(1).strip()
            if "## " in content and len(content) > 200:
                return content

        # ── 4: Raw markdown in the response body ────────────────
        lines = text.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("# ") and 5 < len(stripped) < 100:
                potential = '\n'.join(lines[i:])
                h2_count = sum(1 for ln in lines[i:] if ln.strip().startswith("## "))
                if h2_count >= 2 and len(potential) > 200:
                    # Trim common footers ("Hope this helps!" etc)
                    potential = re.split(
                        r'\n---\n|^User:', potential, flags=re.MULTILINE
                    )[0]
                    return potential.strip()

        return None

    def _format_tool_results_enhanced(self, results: List[Dict[str, Any]], context: AgentContext) -> str:
        """
        Format tool results with enhanced feedback and validation.
        
        Provides clearer success/failure messages and warns about common mistakes.
        """
        from pathlib import Path
        
        parts = []
        for r in results:
            tool = r.get('tool', 'unknown')
            success = r.get('success', False)
            output = str(r.get('output', ''))[:2000]
            error = r.get('error', '')
            
            # Format based on tool type
            if tool.lower() in ['glob', 'globtool', 'smartglob']:
                if success:
                    # Check if output indicates no files found
                    if 'No files' in output or 'no matches' in output.lower():
                        parts.append(f"[{tool}] ⚠️ No files matched pattern\n{output}")
                    else:
                        parts.append(f"[{tool}] ✓ Success:\n{output}")
                else:
                    parts.append(f"[{tool}] ✗ Failed: {error}")
                    
            elif tool.lower() in ['read', 'readtool']:
                if success:
                    parts.append(f"[{tool}] ✓ File read successfully:\n{output}")
                else:
                    # Provide helpful guidance for file not found errors
                    if 'not found' in error.lower() or 'does not exist' in error.lower():
                        # Extract the attempted path from the error
                        attempted_path = error.split(':')[-1].strip() if ':' in error else "unknown"
                        
                        parts.append(f"""[{tool}] ✗ File not found: {error}

🚨 **CRITICAL ERROR: File Path Hallucination Detected**

You attempted to read a file that doesn't exist. This violates the tool usage protocol.

**What you did wrong:**
- Assumed a file path without verification
- Did not use Glob or LS to discover the actual file structure

**Correct workflow:**
1. Use Glob to discover files: {{"tool": "Glob", "arguments": {{"Pattern": "**/*safety*.py"}}}}
2. Review the results to find the actual path
3. Then Read the discovered file with its absolute path

**DO NOT assume file paths based on conventions. ALWAYS verify first with Glob or LS.**
""")
                    else:
                        parts.append(f"[{tool}] ✗ Failed: {error}")
                        
            elif tool.lower() in ['ls', 'lstool']:
                if success:
                    parts.append(f"[{tool}] ✓ Directory listed:\n{output}")
                else:
                    parts.append(f"[{tool}] ✗ Failed: {error}")
                    
            elif tool.lower() in ['write', 'writetool']:
                if success:
                    parts.append(f"[{tool}] ✓ File written successfully:\n{output}")
                else:
                    parts.append(f"[{tool}] ✗ Failed: {error}")
                    
            else:
                # Generic formatting for other tools
                if success:
                    parts.append(f"[{tool}] Success:\n{output}")
                else:
                    parts.append(f"[{tool}] Failed: {error}")
        
        return "\n\n".join(parts) if parts else "No tool results."
