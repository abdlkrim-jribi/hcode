"""
Unit tests for the MCP support system.
Tests config, transports factory, client manager, bridge, and CLI commands.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from hcode.core.mcp.config import (
    MCPServerConfig, MCPConfig, MCPConfigManager, KNOWN_SERVERS
)
from hcode.core.mcp.transports import (
    StdioTransport, HttpTransport, TransportFactory, MCPTransportError
)
from hcode.core.mcp.client import (
    MCPClient, MCPClientManager, MCPToolInfo, MCPToolError, MCPConnectionError
)
from hcode.core.mcp.bridge import MCPToolBridge, MCPToolRegistry


# ─── MCPServerConfig ──────────────────────────────────────────────────────────

class TestMCPServerConfig:

    def test_stdio_server_config(self):
        cfg = MCPServerConfig(
            id="git", name="Git", transport="stdio",
            command="uvx", args=["mcp-server-git"]
        )
        assert cfg.transport == "stdio"
        assert cfg.command == "uvx"
        assert cfg.enabled is True

    def test_http_server_config(self):
        cfg = MCPServerConfig(
            id="github", name="GitHub", transport="http",
            url="https://api.githubcopilot.com/mcp/"
        )
        assert cfg.transport == "http"
        assert cfg.url == "https://api.githubcopilot.com/mcp/"

    def test_known_servers_exist(self):
        assert "filesystem" in KNOWN_SERVERS
        assert "github" in KNOWN_SERVERS
        assert "git" in KNOWN_SERVERS
        assert "fetch" in KNOWN_SERVERS
        assert "sqlite" in KNOWN_SERVERS

    def test_known_server_filesystem_is_stdio(self):
        assert KNOWN_SERVERS["filesystem"].transport == "stdio"

    def test_known_server_github_is_http(self):
        assert KNOWN_SERVERS["github"].transport == "http"


# ─── MCPConfigManager ─────────────────────────────────────────────────────────

class TestMCPConfigManager:

    def test_empty_config_on_missing_file(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        assert mgr.list_all_servers() == []

    def test_add_server(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        server = KNOWN_SERVERS["git"]
        mgr.add_server(server)
        assert mgr.get_server("git") is not None

    def test_add_duplicate_raises(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        mgr.add_server(KNOWN_SERVERS["git"])
        with pytest.raises(ValueError, match="already exists"):
            mgr.add_server(KNOWN_SERVERS["git"])

    def test_remove_server(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        mgr.add_server(KNOWN_SERVERS["git"])
        mgr.remove_server("git")
        assert mgr.get_server("git") is None

    def test_remove_nonexistent_raises(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        with pytest.raises(ValueError, match="not found"):
            mgr.remove_server("nonexistent")

    def test_list_servers_only_enabled(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        enabled = MCPServerConfig(
            id="git", name="Git", transport="stdio",
            command="uvx", args=["mcp-server-git"], enabled=True
        )
        disabled = MCPServerConfig(
            id="fetch", name="Fetch", transport="stdio",
            command="uvx", args=["mcp-server-fetch"], enabled=False
        )
        mgr.add_server(enabled)
        mgr.add_server(disabled)
        assert len(mgr.list_servers()) == 1
        assert len(mgr.list_all_servers()) == 2

    def test_config_persists_to_disk(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        mgr.add_server(KNOWN_SERVERS["fetch"])
        # reload fresh manager
        mgr2 = MCPConfigManager(root_dir=str(tmp_path))
        assert mgr2.get_server("fetch") is not None

    def test_config_file_is_valid_json(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        mgr.add_server(KNOWN_SERVERS["sqlite"])
        config_file = tmp_path / ".hcode" / "mcp_config.json"
        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert "servers" in data


# ─── TransportFactory ─────────────────────────────────────────────────────────

class TestTransportFactory:

    def test_creates_stdio_transport(self):
        t = TransportFactory.create(KNOWN_SERVERS["filesystem"])
        assert isinstance(t, StdioTransport)

    def test_creates_http_transport(self):
        t = TransportFactory.create(KNOWN_SERVERS["github"])
        assert isinstance(t, HttpTransport)

    def test_raises_for_unknown_transport(self):
        cfg = MCPServerConfig(
            id="bad", name="Bad", transport="stdio",
            command="x", args=[]
        )
        cfg.transport = "ftp"  # bypass pydantic
        with pytest.raises((ValueError, MCPTransportError)):
            TransportFactory.create(cfg)

    def test_stdio_transport_server_id(self):
        t = TransportFactory.create(KNOWN_SERVERS["git"])
        assert t.server_id == "git"

    def test_http_transport_server_id(self):
        t = TransportFactory.create(KNOWN_SERVERS["github"])
        assert t.server_id == "github"


# ─── MCPClientManager ─────────────────────────────────────────────────────────

class TestMCPClientManager:

    def test_no_connected_servers_initially(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        client_mgr = MCPClientManager(mgr)
        assert client_mgr.get_connected_servers() == []

    def test_list_all_tools_empty_initially(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        client_mgr = MCPClientManager(mgr)
        assert client_mgr.list_all_tools() == []

    def test_is_server_connected_false(self, tmp_path):
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        client_mgr = MCPClientManager(mgr)
        assert client_mgr.is_server_connected("github") is False

    def test_connect_unknown_server_raises(self, tmp_path):
        import asyncio
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        client_mgr = MCPClientManager(mgr)
        with pytest.raises((ValueError, MCPConnectionError)):
            asyncio.get_event_loop().run_until_complete(
                client_mgr.connect_server("nonexistent")
            )

    def test_connect_all_empty_config_does_not_crash(self, tmp_path):
        import asyncio
        mgr = MCPConfigManager(root_dir=str(tmp_path))
        client_mgr = MCPClientManager(mgr)
        # Should complete without error even with no servers
        asyncio.get_event_loop().run_until_complete(client_mgr.connect_all())
        assert client_mgr.get_connected_servers() == []


# ─── MCPToolBridge ────────────────────────────────────────────────────────────

class TestMCPToolBridge:

    def _make_tool_info(self):
        return MCPToolInfo(
            name="list_issues",
            description="List GitHub issues",
            input_schema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository name"},
                    "limit": {"type": "integer", "description": "Max results"}
                },
                "required": ["repo"]
            },
            server_id="github"
        )

    def test_is_mcp_tool_flag(self):
        assert MCPToolBridge.IS_MCP_TOOL is True

    def test_name_prefixed_correctly(self, tmp_path):
        info = self._make_tool_info()
        client_mgr = MagicMock()
        bridge = MCPToolBridge(info, client_mgr)
        assert bridge.name == "mcp_github_list_issues"

    def test_description_prefixed(self, tmp_path):
        info = self._make_tool_info()
        client_mgr = MagicMock()
        bridge = MCPToolBridge(info, client_mgr)
        assert "[MCP:github]" in bridge.get_description()

    def test_parameters_converted(self, tmp_path):
        info = self._make_tool_info()
        client_mgr = MagicMock()
        bridge = MCPToolBridge(info, client_mgr)
        params = bridge.get_parameters()
        assert len(params) == 2
        param_names = [p.name for p in params]
        assert "repo" in param_names
        assert "limit" in param_names

    def test_required_parameter_marked(self, tmp_path):
        info = self._make_tool_info()
        client_mgr = MagicMock()
        bridge = MCPToolBridge(info, client_mgr)
        params = {p.name: p for p in bridge.get_parameters()}
        assert params["repo"].required is True
        assert params["limit"].required is False

    def test_execute_success(self, tmp_path):
        import asyncio
        info = self._make_tool_info()
        client_mgr = AsyncMock()
        client_mgr.call_tool = AsyncMock(return_value="issue list result")
        bridge = MCPToolBridge(info, client_mgr)
        result = asyncio.get_event_loop().run_until_complete(
            bridge.execute(repo="owner/repo")
        )
        assert result.success is True
        assert "issue list result" in str(result.output)

    def test_execute_tool_error(self, tmp_path):
        import asyncio
        info = self._make_tool_info()
        client_mgr = AsyncMock()
        client_mgr.call_tool = AsyncMock(side_effect=MCPToolError("tool failed"))
        bridge = MCPToolBridge(info, client_mgr)
        result = asyncio.get_event_loop().run_until_complete(
            bridge.execute(repo="owner/repo")
        )
        assert result.success is False
        assert "tool failed" in result.error


# ─── MCPToolRegistry ──────────────────────────────────────────────────────────

class TestMCPToolRegistry:

    def test_list_registered_empty_initially(self, tmp_path):
        client_mgr = MagicMock()
        client_mgr.list_all_tools.return_value = []
        tool_manager = MagicMock()
        registry = MCPToolRegistry(client_mgr, tool_manager)
        assert registry.list_registered_tools() == []

    def test_get_mcp_tool_names_empty(self, tmp_path):
        client_mgr = MagicMock()
        client_mgr.list_all_tools.return_value = []
        tool_manager = MagicMock()
        registry = MCPToolRegistry(client_mgr, tool_manager)
        assert registry.get_mcp_tool_names() == []

    def test_register_all_mcp_tools(self, tmp_path):
        import asyncio
        tool_info = MCPToolInfo(
            name="search", description="Search", 
            input_schema={"type": "object", "properties": {}},
            server_id="fetch"
        )
        client_mgr = MagicMock()
        client_mgr.list_all_tools.return_value = [tool_info]
        tool_manager = MagicMock()
        tool_manager.tool_registry = MagicMock()
        registry = MCPToolRegistry(client_mgr, tool_manager)
        asyncio.get_event_loop().run_until_complete(
            registry.register_all_mcp_tools()
        )
        tool_manager.tool_registry.register.assert_called_once()
        assert "mcp_fetch_search" in registry.get_mcp_tool_names()
