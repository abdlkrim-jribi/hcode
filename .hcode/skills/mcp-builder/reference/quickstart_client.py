"""
MCP Client Quick-Start Template
================================
A minimal MCP client that connects to a stdio server.

Usage:
    python quickstart_client.py
"""
import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    """Connect to an MCP server and exercise its tools."""

    # Configure the server to connect to
    server_params = StdioServerParameters(
        command="python",
        args=["quickstart_server.py"],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Step 1: Initialize
            await session.initialize()
            print("✅ Connected to server\n")

            # Step 2: Discover tools
            tools_result = await session.list_tools()
            print("📦 Available tools:")
            for tool in tools_result.tools:
                print(f"   • {tool.name}: {tool.description}")
            print()

            # Step 3: Call tools
            # Echo
            result = await session.call_tool("echo", {"message": "Hello MCP!"})
            print(f"🔊 echo: {result.content[0].text}")

            # List directory
            result = await session.call_tool(
                "list_directory",
                {"path": ".", "pattern": "*.py"},
            )
            data = json.loads(result.content[0].text)
            print(f"📁 list_directory: {data['entries'][:3]}")

            # Step 4: Read resources
            resources = await session.list_resources()
            print(f"\n📄 Resources: {[r.uri for r in resources.resources]}")

            print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
