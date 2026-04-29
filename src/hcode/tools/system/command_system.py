"""
Custom command system for Hcode.
Supports slash commands and skills similar to Hcode.
"""

import os
from pathlib import Path
from typing import Dict, Optional, List

import yaml
from dataclasses import dataclass, field

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class SlashCommand:
    """Represents a custom slash command"""

    def __init__(self, name: str, description: str, prompt: str):
        """
        Initialize slash command.

        Args:
            name: Command name (without /)
            description: Command description
            prompt: Prompt template to execute
        """
        self.name = name
        self.description = description
        self.prompt = prompt

    def execute(self, args: Optional[str] = None) -> str:
        """Execute command and return expanded prompt"""
        if args:
            return self.prompt.replace("{args}", args)
        return self.prompt


class Skill:
    """Represents a reusable skill"""

    def __init__(self, name: str, description: str, prompt: str, category: Optional[str] = None, folder_path=None):
        """
        Initialize skill.

        Args:
            name: Skill name
            description: Skill description
            prompt: Skill prompt template
            category: Optional category
            folder_path: Absolute path to skill folder (None for legacy flat-file skills)
        """
        self.name = name
        self.description = description
        self.prompt = prompt
        self.category = category
        self.folder_path = folder_path

    def execute(self, context: Optional[Dict] = None) -> str:
        """Execute skill with context"""
        prompt = self.prompt

        # Auto-inject skill folder path
        if self.folder_path:
            prompt = prompt.replace("{skill_dir}", str(self.folder_path))

        if context:
            # Handle string context (autofill if single placeholder or common keys)
            if isinstance(context, str):
                import re
                # Find all placeholders
                matches = re.findall(r"\{(\w+)\}", prompt)
                unique_placeholders = list(set(matches))

                if len(unique_placeholders) == 1:
                    # Single placeholder - assign string to it
                    context = {unique_placeholders[0]: context}
                else:
                    # Fallback context wrapper
                    context = {
                        "input": context,
                        "text": context,
                        "content": context,
                        "file_content": context
                    }

            if isinstance(context, dict):
                for key, value in context.items():
                    prompt = prompt.replace(f"{{{key}}}", str(value))

        return prompt


class CommandRegistry:
    """Registry for slash commands and skills"""

    def __init__(self, root_dir: Optional[str] = None):
        """
        Initialize command registry.

        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir or os.getcwd())
        self.commands: Dict[str, SlashCommand] = {}
        self.skills: Dict[str, Skill] = {}

        self._load_commands()
        self._load_skills()

    def _load_commands(self):
        """Load slash commands from .hcode/commands directory"""
        commands_dir = self.root_dir / ".hcode" / "commands"

        if not commands_dir.exists():
            return

        for cmd_file in commands_dir.glob("*.md"):
            # Read command file
            with open(cmd_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract frontmatter if present
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1])
                        prompt = parts[2].strip()
                        description = frontmatter.get("description", "")
                    except:
                        prompt = content
                        description = ""
                else:
                    prompt = content
                    description = ""
            else:
                prompt = content
                description = ""

            # Register command
            cmd_name = cmd_file.stem
            self.commands[cmd_name] = SlashCommand(
                name=cmd_name, description=description, prompt=prompt
            )

    def _load_single_skill(self, skill_file: Path, folder_path=None):
        """Parse a single skill .md file and register it.

        Args:
            skill_file: Path to the .md file (SKILL.md or legacy flat file)
            folder_path: If folder-based, path to the skill folder
        """
        try:
            content = skill_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return

        if not content.startswith("---"):
            return

        parts = content.split("---", 2)
        if len(parts) < 3:
            return

        try:
            frontmatter = yaml.safe_load(parts[1])
            if not isinstance(frontmatter, dict):
                return
        except yaml.YAMLError:
            return

        prompt = parts[2].strip()
        skill_name = folder_path.name if folder_path else skill_file.stem

        self.skills[skill_name] = Skill(
            name=skill_name,
            description=frontmatter.get("description", ""),
            prompt=prompt,
            category=frontmatter.get("category"),
            folder_path=folder_path.resolve() if folder_path else None,
        )

    def _load_skills(self):
        """Load skills from .hcode/skills directory.

        Supports two formats:
        1. Folder-based (preferred): .hcode/skills/<name>/SKILL.md
        2. Legacy flat-file: .hcode/skills/<name>.md
        """
        skills_dir = self.root_dir / ".hcode" / "skills"
        if not skills_dir.exists():
            return

        # Phase 1: folder-based skills
        for entry in sorted(skills_dir.iterdir()):
            if entry.is_dir():
                skill_md = entry / "SKILL.md"
                if skill_md.exists():
                    self._load_single_skill(skill_md, folder_path=entry)

        # Phase 2: legacy flat-file skills (don't overwrite folder-based)
        for skill_file in sorted(skills_dir.glob("*.md")):
            if skill_file.stem not in self.skills:
                self._load_single_skill(skill_file, folder_path=None)

    def get_command(self, name: str) -> Optional[SlashCommand]:
        """Get slash command by name"""
        return self.commands.get(name)

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get skill by name"""
        return self.skills.get(name)

    def list_commands(self) -> List[SlashCommand]:
        """List all available commands"""
        return list(self.commands.values())

    def list_skills(self, category: Optional[str] = None) -> List[Skill]:
        """List all available skills"""
        if category:
            return [s for s in self.skills.values() if s.category == category]
        return list(self.skills.values())


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    content: str
    is_command: bool = False
    turbo: bool = False


class Workflow:
    """Represents a file-based workflow from .hcode/workflows/*.md"""

    def __init__(self, name: str, description: str,
                 steps: List[WorkflowStep], turbo_all: bool = False,
                 file_path: Optional[Path] = None):
        self.name = name
        self.description = description
        self.steps = steps
        self.turbo_all = turbo_all
        self.file_path = file_path

    @staticmethod
    def parse(name: str, content: str,
              file_path: Optional[Path] = None) -> "Workflow":
        """Parse a workflow markdown file into a Workflow object"""
        description = ""
        turbo_all = False
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1])
                    if isinstance(fm, dict):
                        description = fm.get("description", "")
                except yaml.YAMLError:
                    pass
                body = parts[2].strip()

        steps: List[WorkflowStep] = []
        pending_turbo = False
        COMMAND_PREFIXES = (
            "npm ", "git ", "python ", "pip ", "docker ",
            "make ", "yarn ", "bash ", "sh ", "pytest ",
            "black ", "ruff ", "mypy ", "isort ",
        )

        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == "// turbo-all":
                turbo_all = True
                continue
            if stripped == "// turbo":
                pending_turbo = True
                continue

            raw = stripped
            if len(stripped) > 2 and stripped[0].isdigit() and stripped[1] == ".":
                raw = stripped[2:].strip()

            is_command = raw.startswith(COMMAND_PREFIXES)
            steps.append(WorkflowStep(
                content=raw,
                is_command=is_command,
                turbo=pending_turbo or turbo_all,
            ))
            pending_turbo = False

        return Workflow(
            name=name,
            description=description,
            steps=steps,
            turbo_all=turbo_all,
            file_path=file_path,
        )


class WorkflowManager:
    """Discovers and manages workflows from .hcode/workflows/*.md"""

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = Path(root_dir or os.getcwd())
        self.workflows: Dict[str, Workflow] = {}
        self._load_workflows()

    def _load_workflows(self):
        workflows_dir = self.root_dir / ".hcode" / "workflows"
        if not workflows_dir.exists():
            return
        for wf_file in sorted(workflows_dir.glob("*.md")):
            try:
                content = wf_file.read_text(encoding="utf-8")
                workflow = Workflow.parse(
                    name=wf_file.stem,
                    content=content,
                    file_path=wf_file.resolve(),
                )
                self.workflows[wf_file.stem] = workflow
            except Exception:
                continue

    def get_workflow(self, name: str) -> Optional[Workflow]:
        return self.workflows.get(name)

    def list_workflows(self) -> List[Workflow]:
        return list(self.workflows.values())

    def is_trusted_path(self, file_path: Path) -> bool:
        trusted = (self.root_dir / ".hcode" / "workflows").resolve()
        try:
            file_path.resolve().relative_to(trusted)
            return True
        except ValueError:
            return False


class WorkflowTool(BaseTool):
    """
    Execute file-based workflows from .hcode/workflows/.
    Triggered via /workflow-name. Supports turbo mode for
    auto-running command steps without user confirmation.
    """

    def __init__(self, command_registry: CommandRegistry):
        super().__init__()
        self.category = ToolCategory.CUSTOM
        self.workflow_manager = WorkflowManager(
            root_dir=str(command_registry.root_dir)
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                "workflow",
                "string",
                "Workflow name to execute (e.g., 'deploy' for /deploy)",
                required=True,
            ),
        ]

    def get_description(self) -> str:
        base_desc = super().get_description()
        workflows = self.workflow_manager.list_workflows()
        if not workflows:
            return base_desc
        wf_list = "\n\nAvailable Workflows:"
        for wf in workflows:
            desc = f" - {wf.description}" if wf.description else ""
            turbo_tag = " [turbo-all]" if wf.turbo_all else ""
            wf_list += f"\n- /{wf.name}{desc}{turbo_tag}"
        return base_desc + wf_list

    async def execute(self, workflow: str) -> ToolResult:
        try:
            name = workflow.lstrip("/")
            wf = self.workflow_manager.get_workflow(name)

            if not wf:
                available = ", ".join(
                    f"/{w.name}" for w in self.workflow_manager.list_workflows()
                )
                return ToolResult(
                    success=False, output=None,
                    error=f"Workflow not found: '{name}'. Available: {available}",
                )

            if wf.file_path and not self.workflow_manager.is_trusted_path(wf.file_path):
                return ToolResult(
                    success=False, output=None,
                    error=f"Security: workflow '{name}' is outside trusted directory.",
                )

            if wf.turbo_all:
                from hcode.core.session_manager import get_session_manager
                get_session_manager().grant_permission("Bash", None)

            step_instructions = []
            for i, step in enumerate(wf.steps, 1):
                if step.is_command and step.turbo and not wf.turbo_all:
                    from hcode.core.session_manager import get_session_manager
                    get_session_manager().grant_permission("Bash", step.content)

                step_instructions.append({
                    "index": i,
                    "content": step.content,
                    "is_command": step.is_command,
                    "turbo": step.turbo,
                })

            return ToolResult(
                success=True,
                output=(
                    f"Workflow '{name}': {wf.description}\n"
                    f"Execute these {len(wf.steps)} steps in order:\n" +
                    "\n".join(
                        f"{s['index']}. {'[AUTO] ' if s['turbo'] else ''}{s['content']}"
                        for s in step_instructions
                    )
                ),
                metadata={
                    "workflow": name,
                    "description": wf.description,
                    "turbo_all": wf.turbo_all,
                    "steps": step_instructions,
                },
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class SlashCommandTool(BaseTool):
    """
    Execute slash commands within the conversation.
    """

    def __init__(self, command_registry: CommandRegistry):
        super().__init__()
        self.category = ToolCategory.CUSTOM
        self.command_registry = command_registry

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                "command",
                "string",
                "Slash command to execute (e.g., '/review-pr 123')",
                required=True,
            ),
        ]

    async def execute(self, command: str) -> ToolResult:
        """Execute slash command"""
        try:
            # Parse command
            if not command.startswith("/"):
                return ToolResult(success=False, output=None, error="Command must start with /")

            parts = command[1:].split(maxsplit=1)
            cmd_name = parts[0]
            cmd_args = parts[1] if len(parts) > 1 else None

            # Get command
            slash_cmd = self.command_registry.get_command(cmd_name)

            if not slash_cmd:
                available = ", ".join([f"/{c.name}" for c in self.command_registry.list_commands()])
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Command not found: {cmd_name}. Available: {available}",
                )

            # Execute command
            expanded_prompt = slash_cmd.execute(cmd_args)

            return ToolResult(
                success=True,
                output=expanded_prompt,
                metadata={
                    "command": cmd_name,
                    "args": cmd_args,
                    "description": slash_cmd.description,
                },
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class SkillTool(BaseTool):
    """
    Invoke skills within the conversation.
    """

    def __init__(self, command_registry: CommandRegistry, agent_orchestrator=None):
        super().__init__()
        self.category = ToolCategory.CUSTOM
        self.command_registry = command_registry
        self.agent_orchestrator = agent_orchestrator

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("skill", "string", "Skill name to invoke", required=True),
            ToolParameter("context", "object", "Context variables for skill", default=None),
        ]

    def get_description(self) -> str:
        """Get description with list of available skills"""
        base_desc = super().get_description()
        skills = self.command_registry.list_skills()

        if not skills:
            return base_desc

        skill_list = "\n\nAvailable Skills:"
        for skill in skills:
            desc = f" - {skill.description}" if skill.description else ""
            folder_tag = " [folder]" if skill.folder_path else ""
            skill_list += f"\n- {skill.name}{desc}{folder_tag}"

        return base_desc + skill_list

    async def execute(self, skill: str, context: Optional[Dict] = None) -> ToolResult:
        """Execute skill"""
        try:
            # Get skill
            skill_obj = self.command_registry.get_skill(skill)

            if not skill_obj:
                available = ", ".join([s.name for s in self.command_registry.list_skills()])
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Skill not found: {skill}. Available: {available}",
                )

            # Expand prompt
            expanded_prompt = skill_obj.execute(context)

            # Execute with LLM if orchestrator is available
            if self.agent_orchestrator:
                from hcode.providers import Message

                # Select provider
                provider = self.agent_orchestrator.provider_selector.select_provider()

                # Execute
                messages = [Message(role="user", content=expanded_prompt)]
                response = await provider.generate_completion(messages=messages, stream=False)

                output = response.content
            else:
                # Fallback to returning prompt (for tests/legacy)
                output = expanded_prompt

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "skill": skill,
                    "category": skill_obj.category,
                    "description": skill_obj.description,
                    "skill_dir": str(skill_obj.folder_path) if skill_obj.folder_path else None,
                    "executed_prompt": expanded_prompt if self.agent_orchestrator else None
                },
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class HookSystem:
    """
    Hook system for custom workflows.
    Executes shell commands in response to events.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize hook system.

        Args:
            config: Hook configuration
        """
        self.hooks: Dict[str, List[str]] = config or {}

    async def trigger(self, event: str, context: Optional[Dict] = None) -> List[ToolResult]:
        """Trigger hooks for an event"""
        import subprocess

        if event not in self.hooks:
            return []

        results = []

        for command in self.hooks[event]:
            # Substitute context variables
            if context:
                for key, value in context.items():
                    command = command.replace(f"${{{key}}}", str(value))

            # Execute hook
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=30
                )

                results.append(
                    ToolResult(
                        success=result.returncode == 0,
                        output=result.stdout,
                        error=result.stderr if result.returncode != 0 else None,
                        metadata={"event": event, "command": command},
                    )
                )

            except Exception as e:
                results.append(
                    ToolResult(
                        success=False,
                        output=None,
                        error=str(e),
                        metadata={"event": event, "command": command},
                    )
                )

        return results
