"""
Context injection for system prompts.

This module handles building system prompts with all necessary context
including tool documentation, workspace info, memory, and task context.
"""

from pathlib import Path
from typing import Optional, Any


class ContextInjector:
    """
    Construct system prompts with context for the LLM.
    
    Injects:
    - Tool documentation
    - Workspace/root directory information
    - Memory context (if available)
    - Current task.md and implementation_plan.md
    """
    
    def __init__(
        self,
        root_dir: Path,
        memory_manager: Optional[Any] = None,
        autonomous_mode: bool = False,
    ):
        """
        Initialize the context injector.
        
        Args:
            root_dir: Project root directory
            memory_manager: Optional memory manager for context
            autonomous_mode: Whether agent is running autonomously
        """
        self.root_dir = Path(root_dir)
        self.memory_manager = memory_manager
        self.autonomous_mode = autonomous_mode
    
    def build_system_prompt(
        self,
        provider: Any,
        query: Optional[str] = None,
    ) -> str:
        """
        Build complete system prompt with all context.
        
        Args:
            provider: Current LLM provider
            query: Optional user query for memory context
            
        Returns:
            Complete system prompt string
        """
        # Get base system prompt from provider
        if hasattr(provider, "get_system_prompt_for_coding"):
            base_prompt = provider.get_system_prompt_for_coding()
        else:
            base_prompt = self._get_default_system_prompt()
        
        # Add tool documentation
        base_prompt = self._inject_tool_documentation(base_prompt)
        
        # Add user information (workspace context)
        base_prompt = self._inject_user_information(base_prompt)
        
        # Add memory context
        if self.memory_manager and query:
            base_prompt = self._inject_memory_context(base_prompt, query)
        
        # Add task context (task.md, implementation_plan.md)
        base_prompt = self._inject_task_context(base_prompt)
        
        return base_prompt
    
    def _inject_tool_documentation(self, prompt: str) -> str:
        """Inject tool documentation into prompt."""
        try:
            from hcode.config.tools import get_tools_config
            tools_config = get_tools_config()
            tool_docs = tools_config.get_tool_documentation()
            return prompt + "\n\n" + tool_docs
        except ImportError:
            return prompt
    
    def _inject_user_information(self, prompt: str) -> str:
        """Inject workspace and root directory context."""
        import platform
        
        os_name = platform.system()
        user_info = f"""
<user_information>
The USER's OS version is {os_name}.
The user has 1 active workspace defined by the following root directory:
{self.root_dir} -> main

Code relating to the user's requests should be written in the locations listed above.
Avoid writing project code files to tmp, in the .gemini dir, or directly to the Desktop and similar folders unless explicitly asked.
</user_information>"""
        
        return prompt + user_info
    
    def _inject_memory_context(self, prompt: str, query: str) -> str:
        """Inject relevant memory context."""
        if not self.memory_manager:
            return prompt
        
        try:
            # Get relevant memories
            memories = self.memory_manager.recall(query, top_k=5)
            
            if memories:
                memory_text = "\n<relevant_memories>\n"
                for i, mem in enumerate(memories, 1):
                    content = mem.get("content", "")
                    memory_type = mem.get("type", "context")
                    memory_text += f"{i}. [{memory_type}] {content}\n"
                memory_text += "</relevant_memories>\n"
                
                return prompt + memory_text
        except Exception:
            pass
        
        return prompt
    
    def _inject_task_context(self, prompt: str) -> str:
        """Inject current task.md and implementation_plan.md context."""
        task_context = ""
        
        # Check for .hcode directory
        hcode_dir = self.root_dir / ".hcode"
        if not hcode_dir.exists():
            return prompt
        
        # Read task.md
        task_file = hcode_dir / "task.md"
        if task_file.exists():
            try:
                task_content = task_file.read_text(encoding="utf-8")
                if task_content.strip():
                    task_context += f"\n<current_task>\n{task_content}\n</current_task>\n"
            except Exception:
                pass
        
        # Read implementation_plan.md
        plan_file = hcode_dir / "implementation_plan.md"
        if plan_file.exists():
            try:
                plan_content = plan_file.read_text(encoding="utf-8")
                if plan_content.strip():
                    task_context += f"\n<implementation_plan>\n{plan_content}\n</implementation_plan>\n"
            except Exception:
                pass
        
        return prompt + task_context
    
    def _get_default_system_prompt(self) -> str:
        """Get a default system prompt if provider doesn't provide one."""
        return """You are Hcode, an AI coding assistant.
You help users with coding tasks by reading, writing, and modifying files.
When given a task, analyze it carefully and execute the necessary steps.
Use the available tools to interact with the codebase.
Always explain your reasoning and actions clearly."""
