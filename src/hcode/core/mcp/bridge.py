"""
MCP-to-hcode tool bridge.

Wraps MCP tools discovered from connected servers as native hcode BaseTool
instances so the ToolManager can register and invoke them transparently.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from hcode.core.mcp.client import MCPClientManager, MCPToolError, MCPToolInfo
from hcode.tools.base.base_tool import BaseTool, ToolCategory, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class MCPToolBridge(BaseTool):
    """Bridge that exposes a single MCP tool as a native hcode BaseTool."""

    IS_MCP_TOOL: bool = True

    def __init__(self, tool_info: MCPToolInfo, client_manager: MCPClientManager) -> None:
        """
        Args:
            tool_info:      Metadata for the MCP tool to wrap.
            client_manager: Manager used to dispatch actual tool calls.
        """
        super().__init__()
        self._tool_info = tool_info
        self._client_manager = client_manager
        # Prefix name to avoid collisions with native tools
        self.name = f"mcp_{tool_info.server_id}_{tool_info.name}"
        self.category = ToolCategory.CUSTOM

    def get_description(self) -> str:
        """Return the tool description prefixed with the originating server id."""
        return f"[MCP:{self._tool_info.server_id}] {self._tool_info.description}"

    def get_parameters(self) -> List[ToolParameter]:
        """
        Convert the tool's JSON Schema input_schema to a list of ToolParameters.

        Handles: string, number, integer, boolean, object, array types.
        Parameters listed in the schema's "required" array are marked required=True.
        """
        schema = self._tool_info.input_schema
        if not isinstance(schema, dict):
            return []

        properties = schema.get("properties", {})
        required_names = set(schema.get("required", []))
        params: List[ToolParameter] = []

        for param_name, param_schema in properties.items():
            params.append(
                ToolParameter(
                    name=param_name,
                    type=param_schema.get("type", "string"),
                    description=param_schema.get("description", ""),
                    required=param_name in required_names,
                )
            )

        return params

    async def execute(self, **kwargs) -> ToolResult:
        """
        Dispatch the tool call to the MCP server and return a ToolResult.

        On MCPToolError the call is surfaced as a failed ToolResult rather
        than an exception, consistent with how other hcode tools handle errors.
        """
        server_id = self._tool_info.server_id
        tool_name = self._tool_info.name

        try:
            result = await self._client_manager.call_tool(server_id, tool_name, kwargs)
            return ToolResult(
                success=True,
                output=result,
                metadata={"server_id": server_id, "tool_name": tool_name},
            )
        except MCPToolError as exc:
            return ToolResult(success=False, output=None, error=str(exc))
        except Exception as exc:
            return ToolResult(
                success=False,
                output=None,
                error=f"[MCP:{server_id}] Unexpected error calling '{tool_name}': {exc}",
            )


class MCPToolRegistry:
    """
    Manages the lifecycle of MCP tool bridges inside hcode's ToolManager.

    Keeps an internal record of which tool names belong to which server so
    that per-server unregistration is clean and precise.
    """

    def __init__(self, client_manager: MCPClientManager, tool_manager) -> None:
        """
        Args:
            client_manager: Source of discovered MCP tools.
            tool_manager:   hcode ToolManager whose tool_registry receives the bridges.
        """
        self._client_manager = client_manager
        self._tool_manager = tool_manager
        # server_id -> set of registered tool names (lowercased)
        self._registered: dict[str, set[str]] = {}

    async def register_all_mcp_tools(self) -> None:
        """
        Create and register a MCPToolBridge for every tool on every connected server.

        Individual registration failures are logged as warnings and do not stop
        other tools from being registered.
        """
        all_tools = self._client_manager.list_all_tools()

        # Group by server
        by_server: dict[str, list[MCPToolInfo]] = {}
        for tool_info in all_tools:
            by_server.setdefault(tool_info.server_id, []).append(tool_info)

        for server_id, tools in by_server.items():
            registered_names: set[str] = set()
            for tool_info in tools:
                try:
                    bridge = MCPToolBridge(tool_info, self._client_manager)
                    self._tool_manager.tool_registry.register(bridge)
                    registered_names.add(bridge.name.lower())
                except Exception as exc:
                    logger.warning(
                        "Failed to register MCP tool '%s' from server '%s': %s",
                        tool_info.name,
                        server_id,
                        exc,
                    )

            self._registered.update({server_id: registered_names})
            logger.info("Registered %d MCP tool(s) from server '%s'", len(registered_names), server_id)

    def unregister_server_tools(self, server_id: str) -> None:
        """
        Remove all tools originating from *server_id* from the ToolManager registry.

        No-op if no tools from that server are currently registered.
        """
        tool_names = self._registered.pop(server_id, set())
        if not tool_names:
            return

        registry_tools = self._tool_manager.tool_registry.tools
        for name in tool_names:
            registry_tools.pop(name, None)

        logger.info("Unregistered %d MCP tool(s) from server '%s'", len(tool_names), server_id)

    def list_registered_tools(self) -> List[str]:
        """Return the lowercased tool names currently registered in the ToolManager."""
        names: List[str] = []
        for server_names in self._registered.values():
            names.extend(server_names)
        return names

    def get_mcp_tool_names(self) -> List[str]:
        """
        Return the full prefixed names for all MCP tools on all connected servers.

        Reflects the current state of client_manager, not what is registered.
        """
        return [
            f"mcp_{t.server_id}_{t.name}"
            for t in self._client_manager.list_all_tools()
        ]
