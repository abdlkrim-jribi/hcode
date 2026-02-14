"""
Custom command system for Hcode.
Supports slash commands and skills similar to Hcode.
"""

import os
from pathlib import Path
from typing import Dict, Optional, List, Callable
import yaml

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

    def __init__(self, name: str, description: str, prompt: str, category: Optional[str] = None):
        """
        Initialize skill.

        Args:
            name: Skill name
            description: Skill description
            prompt: Skill prompt template
            category: Optional category
        """
        self.name = name
        self.description = description
        self.prompt = prompt
        self.category = category

    def execute(self, context: Optional[Dict] = None) -> str:
        """Execute skill with context"""
        prompt = self.prompt

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

    def _load_skills(self):
        """Load skills from .hcode/skills directory"""
        skills_dir = self.root_dir / ".hcode" / "skills"

        if not skills_dir.exists():
            return

        for skill_file in skills_dir.glob("*.md"):
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1])
                        prompt = parts[2].strip()

                        skill_name = skill_file.stem
                        self.skills[skill_name] = Skill(
                            name=skill_name,
                            description=frontmatter.get("description", ""),
                            prompt=prompt,
                            category=frontmatter.get("category"),
                        )
                    except:
                        pass

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
            skill_list += f"\n- {skill.name}{desc}"
            
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

    def register_hook(self, event: str, command: str):
        """Register a hook for an event"""
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(command)

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
