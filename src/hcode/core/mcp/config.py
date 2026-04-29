"""
MCP configuration and server definitions for HCode.

Manages MCP server configurations stored in .hcode/mcp_config.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server entry."""

    id: str = Field(..., description="Unique identifier, e.g. 'github', 'filesystem'")
    name: str = Field(..., description="Display name for this server")
    transport: Literal["stdio", "http"] = Field(..., description="Transport type: stdio or http")
    command: Optional[str] = Field(None, description="For stdio: the executable, e.g. 'npx'")
    args: list[str] = Field(default_factory=list, description="For stdio: command arguments")
    url: Optional[str] = Field(None, description="For http: the server URL")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables, e.g. API keys")
    enabled: bool = Field(True, description="Whether this server is active")
    description: str = Field("", description="Human-readable description of this server")


class MCPConfig(BaseModel):
    """Full MCP configuration file model."""

    servers: list[MCPServerConfig] = Field(default_factory=list)
    version: str = "1.0"


# ---------------------------------------------------------------------------
# Well-known servers that can be added with a single command
# ---------------------------------------------------------------------------

KNOWN_SERVERS: dict[str, MCPServerConfig] = {
    "filesystem": MCPServerConfig(
        id="filesystem",
        name="Filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "."],
        description="Access and manipulate local files",
    ),
    "github": MCPServerConfig(
        id="github",
        name="GitHub",
        transport="http",
        url="https://api.githubcopilot.com/mcp/",
        description="GitHub integration via MCP",
    ),
    "git": MCPServerConfig(
        id="git",
        name="Git",
        transport="stdio",
        command="uvx",
        args=["mcp-server-git"],
        description="Git repository operations",
    ),
    "fetch": MCPServerConfig(
        id="fetch",
        name="Fetch",
        transport="stdio",
        command="uvx",
        args=["mcp-server-fetch"],
        description="HTTP fetch and web content retrieval",
    ),
    "sqlite": MCPServerConfig(
        id="sqlite",
        name="SQLite",
        transport="stdio",
        command="uvx",
        args=["mcp-server-sqlite"],
        description="SQLite database access",
    ),
}


class MCPConfigManager:
    """Manages MCP server configurations stored in .hcode/mcp_config.json."""

    def __init__(self, root_dir: Optional[str] = None) -> None:
        """
        Initialize the config manager.

        Args:
            root_dir: Project root directory. Defaults to current working directory.
        """
        self.root_dir = Path(root_dir) if root_dir else Path(os.getcwd())
        self.config_path = self.root_dir / ".hcode" / "mcp_config.json"

    def load(self) -> MCPConfig:
        """
        Read and parse the MCP config JSON file.

        Returns:
            Parsed MCPConfig. Returns an empty config if the file does not exist.
        """
        if not self.config_path.exists():
            return MCPConfig()
        data = json.loads(self.config_path.read_text("utf-8"))
        return MCPConfig.model_validate(data)

    def save(self, config: MCPConfig) -> None:
        """
        Write config to the JSON file, creating .hcode/ directory if needed.

        Args:
            config: The MCPConfig to persist.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(config.model_dump(), indent=2),
            encoding="utf-8",
        )

    def add_server(self, server: MCPServerConfig) -> None:
        """
        Add a server entry to the config.

        Args:
            server: The server configuration to add.

        Raises:
            ValueError: If a server with the same id already exists.
        """
        config = self.load()
        if any(s.id == server.id for s in config.servers):
            raise ValueError(f"Server with id '{server.id}' already exists")
        config.servers.append(server)
        self.save(config)

    def remove_server(self, server_id: str) -> None:
        """
        Remove a server by its id.

        Args:
            server_id: The unique id of the server to remove.

        Raises:
            ValueError: If no server with the given id is found.
        """
        config = self.load()
        original_count = len(config.servers)
        config.servers = [s for s in config.servers if s.id != server_id]
        if len(config.servers) == original_count:
            raise ValueError(f"Server with id '{server_id}' not found")
        self.save(config)

    def get_server(self, server_id: str) -> Optional[MCPServerConfig]:
        """
        Get a server config by its id.

        Args:
            server_id: The unique id to look up.

        Returns:
            The matching MCPServerConfig, or None if not found.
        """
        config = self.load()
        for server in config.servers:
            if server.id == server_id:
                return server
        return None

    def list_servers(self) -> list[MCPServerConfig]:
        """
        Return only enabled server configs.

        Returns:
            List of enabled MCPServerConfig entries.
        """
        return [s for s in self.load().servers if s.enabled]

    def list_all_servers(self) -> list[MCPServerConfig]:
        """
        Return all server configs, including disabled ones.

        Returns:
            List of all MCPServerConfig entries.
        """
        return self.load().servers
