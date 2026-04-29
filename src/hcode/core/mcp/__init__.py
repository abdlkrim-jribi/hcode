"""
MCP (Model Context Protocol) integration for HCode.

Provides configuration, transport, client management, and tool bridging
so MCP server tools appear as native hcode tools.
"""

from hcode.core.mcp.config import (
    MCPServerConfig,
    MCPConfig,
    MCPConfigManager,
    KNOWN_SERVERS,
)
from hcode.core.mcp.transports import (
    StdioTransport,
    HttpTransport,
    TransportFactory,
    MCPTransportError,
)
from hcode.core.mcp.client import (
    MCPClient,
    MCPClientManager,
    MCPToolInfo,
    MCPToolError,
    MCPConnectionError,
)
from hcode.core.mcp.bridge import (
    MCPToolBridge,
    MCPToolRegistry,
)

__all__ = [
    "MCPServerConfig",
    "MCPConfig",
    "MCPConfigManager",
    "KNOWN_SERVERS",
    "StdioTransport",
    "HttpTransport",
    "TransportFactory",
    "MCPTransportError",
    "MCPClient",
    "MCPClientManager",
    "MCPToolInfo",
    "MCPToolError",
    "MCPConnectionError",
    "MCPToolBridge",
    "MCPToolRegistry",
]
