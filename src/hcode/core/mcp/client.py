"""
MCP client implementation for HCode.

Manages connections to MCP servers and exposes their tools for use by the agent.
MCPClient handles a single server; MCPClientManager orchestrates all servers.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any, Optional

from hcode.core.mcp.config import MCPConfigManager, MCPServerConfig
from hcode.core.mcp.transports import MCPTransportError, TransportFactory

logger = logging.getLogger(__name__)


@dataclass
class MCPToolInfo:
    """Metadata for a single tool discovered from an MCP server."""

    name: str
    description: str
    input_schema: dict
    server_id: str


class MCPToolError(Exception):
    """Raised when an MCP tool call fails."""


class MCPConnectionError(Exception):
    """Raised when connecting to an MCP server fails."""


class MCPClient:
    """
    Manages a connection to a single MCP server.

    Handles transport setup, session initialisation, tool discovery, and tool
    invocation for one configured server.
    """

    def __init__(self, config: MCPServerConfig) -> None:
        """
        Args:
            config: Server configuration describing how to connect.
        """
        self._config = config
        self._transport = TransportFactory.create(config)
        self._session: Any = None
        self._session_stack: Optional[AsyncExitStack] = None
        self._tools: dict[str, MCPToolInfo] = {}
        self._connected = False

    async def connect(self) -> None:
        """
        Open the transport and initialise an MCP client session.

        After a successful connect, tools are automatically discovered and
        cached. Call list_tools() or call_tool() afterwards.

        Raises:
            MCPConnectionError: If transport or session setup fails.
        """
        from mcp import ClientSession

        logger.debug("[%s] Connecting to MCP server '%s'", self._config.id, self._config.name)

        try:
            read, write = await self._transport.connect()

            self._session_stack = AsyncExitStack()
            self._session = await self._session_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self._session.initialize()
            self._connected = True

            # Discover tools provided by this server
            await self._discover_tools()

            logger.debug(
                "Connected to MCP server '%s' (%s) — %d tool(s) available",
                self._config.name,
                self._config.id,
                len(self._tools),
            )

        except (MCPTransportError, MCPConnectionError):
            await self._cleanup()
            raise
        except Exception as exc:
            await self._cleanup()
            raise MCPConnectionError(
                f"[{self._config.id}] Failed to establish session: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """
        Close the session and terminate the transport.

        Safe to call even if not currently connected.
        """
        logger.debug("[%s] Disconnecting from MCP server", self._config.id)
        await self._cleanup()

    async def _cleanup(self) -> None:
        """Internal teardown: close session stack then transport."""
        if self._session_stack:
            await self._session_stack.aclose()
        self._session_stack = None
        self._session = None

        if self._transport:
            await self._transport.disconnect()

        self._tools.clear()
        self._connected = False

    async def _discover_tools(self) -> None:
        """
        Query the server for available tools and cache them.

        Populates self._tools keyed by tool name.
        """
        result = await self._session.list_tools()
        self._tools = {
            tool.name: MCPToolInfo(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
                server_id=self._config.id,
            )
            for tool in result.tools
        }
        logger.debug(
            "[%s] Discovered %d tool(s): %s",
            self._config.id,
            len(self._tools),
            list(self._tools.keys()),
        )

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Invoke a tool on the connected server and return its output as a string.

        Args:
            tool_name: Name of the tool to call.
            arguments:  Input arguments matching the tool's input schema.

        Returns:
            The tool's text output, joining multiple content items with newlines.

        Raises:
            MCPToolError: If the client is not connected, the tool is not found,
                          or the tool call itself fails.
        """
        if not self._connected or not self._session:
            raise MCPToolError(f"[{self._config.id}] Not connected")

        if tool_name not in self._tools:
            available = ", ".join(self._tools.keys()) or "(none)"
            raise MCPToolError(
                f"[{self._config.id}] Tool '{tool_name}' not found. Available: {available}"
            )

        try:
            result = await self._session.call_tool(tool_name, arguments)

            parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    parts.append(item.text)
                else:
                    parts.append(str(item))
            return "\n".join(parts)

        except Exception as exc:
            logger.error("[%s] Tool call '%s' failed: %s", self._config.id, tool_name, exc)
            raise MCPToolError(
                f"[{self._config.id}] Tool call '{tool_name}' failed: {exc}"
            ) from exc

    def list_tools(self) -> list[MCPToolInfo]:
        """Return all tools discovered from this server."""
        return list(self._tools.values())

    @property
    def is_connected(self) -> bool:
        """True if the client is currently connected and the session is live."""
        return self._connected

    @property
    def server_id(self) -> str:
        """The unique id of the configured server."""
        return self._config.id


class MCPClientManager:
    """
    Orchestrates connections to all configured MCP servers.

    Uses MCPConfigManager to read which servers are enabled, then manages
    a pool of MCPClient instances — one per server.
    """

    def __init__(self, config_manager: MCPConfigManager) -> None:
        """
        Args:
            config_manager: Provides the list of server configurations.
        """
        self._config_manager = config_manager
        self._clients: dict[str, MCPClient] = {}

    async def connect_all(self) -> None:
        """
        Connect to all enabled servers concurrently.

        Individual failures are logged as warnings and do not prevent other
        servers from connecting. Use get_connected_servers() afterwards to
        see which ones succeeded.
        """
        servers = self._config_manager.list_servers()
        if not servers:
            logger.debug("No enabled MCP servers configured — nothing to connect")
            return

        async def _connect_one(server_config: MCPServerConfig) -> None:
            try:
                client = MCPClient(server_config)
                await client.connect()
                self._clients[server_config.id] = client
            except MCPConnectionError as exc:
                logger.warning("Could not connect to MCP server '%s': %s", server_config.id, exc)
            except Exception as exc:
                logger.warning(
                    "Unexpected error connecting to MCP server '%s': %s",
                    server_config.id,
                    exc,
                )

        await asyncio.gather(*[_connect_one(s) for s in servers])

    async def disconnect_all(self) -> None:
        """Disconnect from all currently connected servers."""
        await asyncio.gather(
            *[client.disconnect() for client in self._clients.values()],
            return_exceptions=True,
        )
        self._clients.clear()

    async def connect_server(self, server_id: str) -> None:
        """
        Connect to a single server by id.

        Args:
            server_id: The id of the server to connect.

        Raises:
            ValueError: If the server is not found in the config.
            MCPConnectionError: If the connection attempt fails.
        """
        server_config = self._config_manager.get_server(server_id)
        if not server_config:
            raise ValueError(f"MCP server '{server_id}' not found in config")
        client = MCPClient(server_config)
        await client.connect()
        self._clients[server_id] = client

    async def disconnect_server(self, server_id: str) -> None:
        """
        Disconnect from a single server by id.

        No-op if the server is not currently connected.
        """
        client = self._clients.pop(server_id, None)
        if client:
            await client.disconnect()

    async def call_tool(self, server_id: str, tool_name: str, arguments: dict) -> str:
        """
        Call a tool on a specific connected server.

        Args:
            server_id:  The id of the target server.
            tool_name:  The name of the tool to invoke.
            arguments:  Arguments for the tool.

        Returns:
            Tool output as a string.

        Raises:
            MCPToolError: If the server is not connected or the tool call fails.
        """
        client = self._clients.get(server_id)
        if not client:
            raise MCPToolError(f"MCP server '{server_id}' is not connected")
        return await client.call_tool(tool_name, arguments)

    def list_all_tools(self) -> list[MCPToolInfo]:
        """Return tools from all currently connected servers."""
        tools: list[MCPToolInfo] = []
        for client in self._clients.values():
            tools.extend(client.list_tools())
        return tools

    def get_connected_servers(self) -> list[str]:
        """Return the ids of all currently connected servers."""
        return list(self._clients)

    def is_server_connected(self, server_id: str) -> bool:
        """Return True if the given server is currently connected."""
        client = self._clients.get(server_id)
        return client.is_connected if client else False
