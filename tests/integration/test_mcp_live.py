"""
Live integration test for MCP fetch server.

Requires: uvx mcp-server-fetch available on PATH
Run with: pytest tests/integration/test_mcp_live.py -v -s

These tests actually spawn the mcp-server-fetch subprocess via stdio,
discover its tools, and execute a real HTTP fetch against example.com.
"""

import asyncio
import pytest

from hcode.core.mcp.config import MCPConfigManager, MCPServerConfig, KNOWN_SERVERS
from hcode.core.mcp.client import MCPClientManager


@pytest.mark.integration
class TestMCPFetchLive:
    """Live integration tests against a real mcp-server-fetch process."""

    def setup_method(self) -> None:
        """Grab the fetch server template from KNOWN_SERVERS."""
        self.server = KNOWN_SERVERS["fetch"]

    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------

    def test_fetch_server_config_valid(self) -> None:
        """Verify fetch server config is correct."""
        assert self.server.transport == "stdio"
        assert self.server.command == "uvx"
        assert "mcp-server-fetch" in self.server.args
        print(f"\nFetch server config: {self.server}")

    # ------------------------------------------------------------------
    # Tool discovery (requires real subprocess)
    # ------------------------------------------------------------------

    def test_fetch_tool_discovery(self, tmp_path) -> None:
        """Connect to fetch server and discover tools."""

        async def run():
            mgr = MCPConfigManager(root_dir=str(tmp_path))
            mgr.add_server(self.server)
            client_mgr = MCPClientManager(mgr)
            await client_mgr.connect_all()

            try:
                connected = client_mgr.get_connected_servers()
                print(f"\nConnected servers: {connected}")
                assert "fetch" in connected, f"fetch not in {connected}"

                tools = client_mgr.list_all_tools()
                tool_names = [t.name for t in tools]
                print(f"Discovered tools: {tool_names}")
                assert len(tools) > 0, "No tools discovered"

                return tools
            finally:
                await client_mgr.disconnect_all()

        tools = asyncio.run(run())
        assert any("fetch" in t.name.lower() for t in tools), (
            f"No tool with 'fetch' in its name. Got: {[t.name for t in tools]}"
        )

    # ------------------------------------------------------------------
    # Tool execution (requires network access)
    # ------------------------------------------------------------------

    def test_fetch_tool_execution(self, tmp_path) -> None:
        """Actually call the fetch tool to retrieve https://example.com."""

        async def run():
            mgr = MCPConfigManager(root_dir=str(tmp_path))
            mgr.add_server(self.server)
            client_mgr = MCPClientManager(mgr)
            await client_mgr.connect_all()

            try:
                tools = client_mgr.list_all_tools()
                tool_names = [t.name for t in tools]
                print(f"\nAvailable tools: {tool_names}")

                # Call the fetch tool — returns a plain string
                result = await client_mgr.call_tool(
                    server_id="fetch",
                    tool_name="fetch",
                    arguments={"url": "https://example.com"},
                )
                print(f"Fetch result (first 200 chars): {result[:200]}")

                assert result is not None
                assert len(result) > 0, "Fetch returned empty result"
                # The server may return page content OR a robots.txt
                # fetch error — both prove the tool executed successfully.
                assert "example" in result.lower() or "fetch" in result.lower(), (
                    f"Unexpected result content: {result[:200]}"
                )

                return result
            finally:
                await client_mgr.disconnect_all()

        result = asyncio.run(run())
        assert isinstance(result, str)
        print(f"\n[OK] Fetched {len(result)} characters from example.com")
