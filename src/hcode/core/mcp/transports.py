"""
MCP transport implementations for HCode.

Handles low-level MCP connections for stdio (subprocess) and HTTP/SSE transports,
wrapping the official mcp Python SDK.
"""

from __future__ import annotations

import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Optional

from hcode.core.mcp.config import MCPServerConfig

logger = logging.getLogger(__name__)

# Type alias for the stream pair returned by connect()
_Streams = tuple[Any, Any]


class MCPTransportError(Exception):
    """Raised when an MCP transport operation fails."""


class StdioTransport:
    """
    Manages a connection to a local MCP server via subprocess (stdio transport).

    Uses mcp.client.stdio.stdio_client under the hood. The subprocess is launched
    on connect() and terminated on disconnect().
    """

    def __init__(self, config: MCPServerConfig) -> None:
        """
        Args:
            config: Server configuration. Must have transport == "stdio".
        """
        self._config = config
        self._exit_stack: Optional[AsyncExitStack] = None
        self._read_stream: Any = None
        self._write_stream: Any = None
        self._connected: bool = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def connect(self) -> _Streams:
        """
        Launch the subprocess and open stdio streams.

        Environment variables from config.env are merged on top of os.environ
        so the subprocess inherits the full current environment plus any overrides.

        Returns:
            (read_stream, write_stream) pair ready for use with mcp.ClientSession.

        Raises:
            MCPTransportError: If the subprocess cannot be started or the
                               connection fails for any reason.
        """
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client

        logger.debug("[%s] Connecting via stdio (command=%s %s)", self._config.id,
                     self._config.command, self._config.args)

        env = {**os.environ, **self._config.env}
        params = StdioServerParameters(
            command=self._config.command,
            args=self._config.args,
            env=env,
        )

        self._exit_stack = AsyncExitStack()
        try:
            read, write = await self._exit_stack.enter_async_context(stdio_client(params))
            self._read_stream = read
            self._write_stream = write
            self._connected = True
            logger.debug("[%s] Connected via stdio", self._config.id)
            return read, write
        except Exception as exc:
            await self._exit_stack.aclose()
            self._exit_stack = None
            logger.error("[%s] stdio connection failed: %s", self._config.id, exc)
            raise MCPTransportError(
                f"[{self._config.id}] Failed to connect via stdio: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """
        Terminate the subprocess and close streams.

        Safe to call even if not currently connected.
        """
        if self._exit_stack is not None:
            logger.debug("[%s] Disconnecting stdio transport", self._config.id)
            await self._exit_stack.aclose()
            self._exit_stack = None
        self._read_stream = None
        self._write_stream = None
        self._connected = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """True if the transport is currently connected."""
        return self._connected

    @property
    def server_id(self) -> str:
        """The unique id of the configured server."""
        return self._config.id


class HttpTransport:
    """
    Manages a connection to a remote MCP server via HTTP/SSE transport.

    Uses mcp.client.sse.sse_client under the hood.
    """

    def __init__(self, config: MCPServerConfig) -> None:
        """
        Args:
            config: Server configuration. Must have transport == "http" and a url set.
        """
        self._config = config
        self._exit_stack: Optional[AsyncExitStack] = None
        self._read_stream: Any = None
        self._write_stream: Any = None
        self._connected: bool = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def connect(self) -> _Streams:
        """
        Open an SSE connection to the remote server URL.

        Returns:
            (read_stream, write_stream) pair ready for use with mcp.ClientSession.

        Raises:
            MCPTransportError: If the URL is missing or the connection fails.
        """
        from mcp.client.sse import sse_client

        if not self._config.url:
            raise MCPTransportError(
                f"[{self._config.id}] HTTP transport requires a url in the server config"
            )

        logger.debug("[%s] Connecting via HTTP/SSE (url=%s)", self._config.id, self._config.url)

        self._exit_stack = AsyncExitStack()
        try:
            read, write = await self._exit_stack.enter_async_context(
                sse_client(self._config.url)
            )
            self._read_stream = read
            self._write_stream = write
            self._connected = True
            logger.debug("[%s] Connected via HTTP/SSE", self._config.id)
            return read, write
        except Exception as exc:
            await self._exit_stack.aclose()
            self._exit_stack = None
            logger.error("[%s] HTTP/SSE connection failed: %s", self._config.id, exc)
            raise MCPTransportError(
                f"[{self._config.id}] Failed to connect via HTTP/SSE: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """
        Close the SSE connection.

        Safe to call even if not currently connected.
        """
        if self._exit_stack is not None:
            logger.debug("[%s] Disconnecting HTTP/SSE transport", self._config.id)
            await self._exit_stack.aclose()
            self._exit_stack = None
        self._read_stream = None
        self._write_stream = None
        self._connected = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """True if the transport is currently connected."""
        return self._connected

    @property
    def server_id(self) -> str:
        """The unique id of the configured server."""
        return self._config.id


class TransportFactory:
    """Static factory that creates the correct transport for a given server config."""

    @staticmethod
    def create(config: MCPServerConfig) -> StdioTransport | HttpTransport:
        """
        Instantiate the appropriate transport based on config.transport.

        Args:
            config: Server configuration specifying which transport to use.

        Returns:
            A StdioTransport for "stdio" configs, HttpTransport for "http" configs.

        Raises:
            ValueError: If config.transport is not a recognised type.
        """
        if config.transport == "stdio":
            return StdioTransport(config)
        if config.transport == "http":
            return HttpTransport(config)
        raise ValueError(
            f"Unsupported transport type '{config.transport}' for server '{config.id}'. "
            "Expected 'stdio' or 'http'."
        )
