---
name: mcp-builder
description: Guide for building MCP clients and servers using the official Python MCP SDK. Covers stdio and HTTP transports, tool discovery, tool execution, async patterns, error handling, and security best practices.
category: integration
---

# MCP Builder Skill

Build **Model Context Protocol (MCP)** clients and servers using the official Python MCP SDK.  
Use this skill when you need to create, integrate, or debug MCP-based tool interfaces.

---

## 🧠 Core Concepts

### What is MCP?
The **Model Context Protocol** is an open standard that enables AI systems to connect with external tools, data sources, and services through a unified interface. It defines three core primitives:

| Primitive    | Description                                   | Example                                |
|-------------|-----------------------------------------------|----------------------------------------|
| **Tools**    | Functions the model can invoke                 | `search_database`, `send_email`        |
| **Resources**| Read-only data the model can reference         | `file://config.json`, `db://users`     |
| **Prompts**  | Reusable prompt templates                      | `summarize`, `translate`               |

### Transport Types
| Transport | Use Case                         | Library             |
|-----------|----------------------------------|---------------------|
| **stdio** | Local subprocess communication    | Built-in            |
| **SSE**   | HTTP Server-Sent Events (legacy)  | `mcp[cli]`          |
| **Streamable HTTP** | Modern HTTP transport  | `mcp[cli]`          |

---

## When to Use

Use this skill when:
- **Building an MCP Server**: Exposing tools/resources to AI agents.
- **Building an MCP Client**: Connecting to and invoking tools on MCP servers.
- **Debugging MCP Connections**: Diagnosing transport, serialization, or tool execution issues.
- **Integrating MCP with LangChain/LangGraph**: Wiring MCP tools into agent workflows.

---

## 1. Installation

```bash
# Core SDK
pip install mcp

# With CLI support (for HTTP transports)
pip install "mcp[cli]"

# For LangChain integration
pip install langchain-mcp-adapters
```

**Requirements:** Python 3.10+

---

## 2. Building an MCP Server

### 2.1 Minimal Server (stdio)

```python
"""Minimal MCP server with a single tool."""
from mcp.server.fastmcp import FastMCP

# Create server instance
mcp = FastMCP(
    name="my-tools",
    version="1.0.0",
)


@mcp.tool()
def greet(name: str) -> str:
    """Greet a user by name.

    Args:
        name: The name of the person to greet.
    """
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 2.2 Server with Multiple Tools

```python
"""MCP server with typed tools, resources, and error handling."""
import json
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP(name="project-tools", version="1.0.0")


# --- Tools ---

@mcp.tool()
def search_files(
    query: str,
    directory: str = ".",
    max_results: int = 10,
) -> str:
    """Search for files matching a query pattern.

    Args:
        query: Search pattern (glob or substring).
        directory: Root directory to search from.
        max_results: Maximum number of results to return.
    """
    from pathlib import Path

    results = []
    root = Path(directory).resolve()

    # Security: prevent path traversal
    if not root.exists():
        return json.dumps({"error": f"Directory not found: {directory}"})

    for path in root.rglob(f"*{query}*"):
        if len(results) >= max_results:
            break
        results.append(str(path.relative_to(root)))

    return json.dumps({"matches": results, "count": len(results)})


@mcp.tool()
def execute_query(
    sql: str,
    database: str = "default",
) -> str:
    """Execute a read-only SQL query against a database.

    Args:
        sql: The SQL query to execute (SELECT only).
        database: Database identifier.
    """
    # Security: reject non-SELECT queries
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are allowed"})

    # Placeholder — replace with actual DB logic
    return json.dumps({
        "status": "ok",
        "query": sql,
        "database": database,
        "rows": [],
    })


# --- Resources ---

@mcp.resource("config://app")
def get_app_config() -> str:
    """Return the application configuration."""
    return json.dumps({
        "app_name": "MyApp",
        "version": "2.0.0",
        "environment": "development",
    })


@mcp.resource("status://health")
def health_check() -> str:
    """Return server health status."""
    return json.dumps({"status": "healthy", "uptime": "OK"})


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 2.3 Server with HTTP Transport (Streamable HTTP)

```python
"""MCP server running over HTTP with Streamable HTTP transport."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="http-tools",
    version="1.0.0",
    host="0.0.0.0",
    port=8080,
)


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely.

    Args:
        expression: A mathematical expression to evaluate.
    """
    import ast
    import operator

    # Safe eval using AST
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op = allowed_ops.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op = allowed_ops.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(operand)
        else:
            raise ValueError(f"Unsupported expression: {type(node).__name__}")

    tree = ast.parse(expression, mode="eval")
    result = _eval(tree.body)
    return str(result)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

---

## 3. Building an MCP Client

### 3.1 Stdio Client

```python
"""MCP client that connects to a server via stdio."""
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # Define how to launch the server
    server_params = StdioServerParameters(
        command="python",
        args=["my_server.py"],
        env=None,  # Inherit environment
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Discover available tools
            tools_result = await session.list_tools()
            print("Available tools:")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description}")

            # Call a tool
            result = await session.call_tool(
                name="greet",
                arguments={"name": "World"},
            )
            print(f"\nResult: {result.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
```

### 3.2 SSE/HTTP Client

```python
"""MCP client that connects to a server via SSE (HTTP)."""
import asyncio

from mcp import ClientSession
from mcp.client.sse import sse_client


async def main():
    server_url = "http://localhost:8080/sse"

    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"Tool: {tool.name}")
                print(f"  Schema: {tool.inputSchema}")

            # Call tool
            result = await session.call_tool(
                name="calculate",
                arguments={"expression": "2 ** 10"},
            )
            print(f"Result: {result.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
```

### 3.3 Streamable HTTP Client

```python
"""MCP client using the modern Streamable HTTP transport."""
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    server_url = "http://localhost:8080/mcp"

    async with streamablehttp_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"Tool: {tool.name} — {tool.description}")

            result = await session.call_tool(
                name="calculate",
                arguments={"expression": "3 + 4 * 2"},
            )
            print(f"Result: {result.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 4. LangChain / LangGraph Integration

### 4.1 Using MCP Tools with LangChain Agents

```python
"""Integrate MCP tools into a LangChain ReAct agent."""
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI  # or any LangChain-compatible LLM


async def main():
    model = ChatOpenAI(model="gpt-4o")

    async with MultiServerMCPClient(
        {
            "math-tools": {
                "command": "python",
                "args": ["math_server.py"],
                "transport": "stdio",
            },
            "file-tools": {
                "url": "http://localhost:8080/sse",
                "transport": "sse",
            },
        }
    ) as client:
        tools = client.get_tools()
        agent = create_react_agent(model, tools)

        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "What is 2^10?"}]}
        )
        print(response["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 5. Advanced Patterns

### 5.1 Context & Lifespan Management

```python
"""Server with managed lifecycle (DB connections, caches, etc.)."""
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP


@dataclass
class AppContext:
    """Shared application state."""
    db_pool: object  # Replace with actual connection pool type


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage the server's lifecycle."""
    # Startup
    db_pool = await create_db_pool()  # Your initialization logic
    try:
        yield AppContext(db_pool=db_pool)
    finally:
        # Shutdown
        await db_pool.close()


mcp = FastMCP(name="db-tools", lifespan=app_lifespan)


@mcp.tool()
def query_users(ctx, limit: int = 10) -> str:
    """Query the users table.

    Args:
        limit: Maximum number of users to return.
    """
    # Access lifespan context via ctx.request_context.lifespan_context
    db = ctx.request_context.lifespan_context.db_pool
    # ... execute query
    return "[]"
```

### 5.2 Structured Error Handling

```python
"""Proper error handling in MCP tools."""
import json
import traceback
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

mcp = FastMCP(name="safe-tools")


def tool_error(message: str, details: Any = None) -> str:
    """Create a standardized error response."""
    error = {"error": message}
    if details:
        error["details"] = str(details)
    return json.dumps(error)


@mcp.tool()
def risky_operation(input_data: str) -> str:
    """Perform an operation with comprehensive error handling.

    Args:
        input_data: Data to process.
    """
    # Input validation
    if not input_data or not input_data.strip():
        return tool_error("Input data cannot be empty")

    if len(input_data) > 10_000:
        return tool_error("Input too large", f"Max 10,000 chars, got {len(input_data)}")

    try:
        # Your logic here
        result = process(input_data)
        return json.dumps({"status": "ok", "result": result})
    except ValueError as e:
        return tool_error("Validation error", str(e))
    except TimeoutError:
        return tool_error("Operation timed out")
    except Exception as e:
        # Log the full traceback server-side
        traceback.print_exc()
        return tool_error("Internal error", str(e))
```

### 5.3 Dynamic Tool Registration

```python
"""Register tools dynamically at runtime."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="dynamic-tools")


def create_crud_tools(entity_name: str):
    """Generate CRUD tools for a given entity."""

    @mcp.tool(name=f"create_{entity_name}")
    def create(data: str) -> str:
        f"""Create a new {entity_name}.

        Args:
            data: JSON data for the new {entity_name}.
        """
        return f"Created {entity_name}: {data}"

    @mcp.tool(name=f"get_{entity_name}")
    def get(id: str) -> str:
        f"""Get a {entity_name} by ID.

        Args:
            id: The {entity_name} identifier.
        """
        return f"Got {entity_name}: {id}"

    @mcp.tool(name=f"delete_{entity_name}")
    def delete(id: str) -> str:
        f"""Delete a {entity_name} by ID.

        Args:
            id: The {entity_name} identifier.
        """
        return f"Deleted {entity_name}: {id}"


# Generate tools for multiple entities
for entity in ["user", "project", "task"]:
    create_crud_tools(entity)
```

---

## 6. Testing MCP Servers

### 6.1 Unit Testing with pytest

```python
"""Test MCP tools using pytest and the MCP test client."""
import json
import pytest
from mcp.server.fastmcp import FastMCP

# Assuming your server module exposes `mcp`
from my_server import mcp


@pytest.fixture
def client():
    """Create a test client for the MCP server."""
    return mcp.test_client()


@pytest.mark.asyncio
async def test_greet_tool(client):
    """Test the greet tool returns correct output."""
    result = await client.call_tool("greet", {"name": "Alice"})
    assert result.content[0].text == "Hello, Alice!"


@pytest.mark.asyncio
async def test_search_files(client):
    """Test file search returns valid JSON."""
    result = await client.call_tool(
        "search_files",
        {"query": "*.py", "directory": ".", "max_results": 5},
    )
    data = json.loads(result.content[0].text)
    assert "matches" in data
    assert "count" in data
    assert isinstance(data["matches"], list)


@pytest.mark.asyncio
async def test_tool_discovery(client):
    """Test that all expected tools are listed."""
    tools = await client.list_tools()
    tool_names = {t.name for t in tools.tools}
    assert "greet" in tool_names
    assert "search_files" in tool_names
```

### 6.2 Testing with MCP Inspector

```bash
# Launch the MCP Inspector for interactive testing
npx @modelcontextprotocol/inspector python my_server.py
```

---

## 7. Security Best Practices

### ⚠️ Critical Rules

1. **Input Validation**: Always validate and sanitize tool inputs.
2. **Path Traversal Prevention**: Resolve paths and check they stay within allowed directories.
3. **No Arbitrary Code Execution**: Never `eval()` or `exec()` user input.
4. **Read-Only by Default**: Tools should be read-only unless write access is explicitly needed.
5. **Timeout Protection**: Set timeouts on external calls and subprocess execution.
6. **Secret Management**: Never expose API keys, tokens, or credentials in tool outputs.

### Path Safety Pattern

```python
from pathlib import Path

ALLOWED_ROOT = Path("/app/data").resolve()


def safe_path(user_path: str) -> Path:
    """Resolve a user-provided path safely."""
    resolved = (ALLOWED_ROOT / user_path).resolve()
    if not str(resolved).startswith(str(ALLOWED_ROOT)):
        raise ValueError(f"Path traversal detected: {user_path}")
    return resolved
```

### Subprocess Safety Pattern

```python
import subprocess


def safe_exec(command: list[str], timeout: int = 30) -> str:
    """Execute a subprocess safely with timeout and output limits."""
    # Allowlist approach
    ALLOWED_COMMANDS = {"ls", "cat", "grep", "find", "wc"}

    if command[0] not in ALLOWED_COMMANDS:
        raise ValueError(f"Command not allowed: {command[0]}")

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,  # NEVER use shell=True with user input
    )

    # Limit output size
    max_output = 50_000
    output = result.stdout[:max_output]
    if len(result.stdout) > max_output:
        output += f"\n... (truncated, total {len(result.stdout)} chars)"

    return output
```

---

## 8. Project Structure

Recommended project layout for an MCP server project:

```
my-mcp-server/
├── pyproject.toml          # Package config with mcp dependency
├── README.md
├── src/
│   └── my_mcp_server/
│       ├── __init__.py
│       ├── server.py        # FastMCP instance + tool definitions
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── file_tools.py
│       │   ├── db_tools.py
│       │   └── api_tools.py
│       ├── resources/
│       │   ├── __init__.py
│       │   └── config.py
│       └── utils/
│           ├── __init__.py
│           ├── validation.py
│           └── security.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_file_tools.py
│   └── test_db_tools.py
└── config/
    └── server_config.yaml
```

### pyproject.toml Example

```toml
[project]
name = "my-mcp-server"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "mcp[cli]>=1.0.0",
]

[project.scripts]
my-mcp-server = "my_mcp_server.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## 9. Debugging Tips

| Symptom                              | Likely Cause                       | Fix                                           |
|--------------------------------------|------------------------------------|-----------------------------------------------|
| Connection refused                   | Server not running / wrong port    | Check `host` and `port` params                |
| Tool not found                       | Tool not registered / typo         | Run `list_tools()` to verify                  |
| `JSONDecodeError`                    | Tool returns non-JSON string       | Return `json.dumps(...)` from tools           |
| `TypeError` on tool call             | Wrong argument types               | Check `inputSchema` for correct types         |
| Timeout on stdio                     | Server stuck / infinite loop       | Add logging + timeout to server operations    |
| `RuntimeError: Event loop closed`    | Nested `asyncio.run()`             | Use `async with` pattern consistently         |

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# For MCP protocol-level debugging
logging.getLogger("mcp").setLevel(logging.DEBUG)
```

---

## 🛠️ Implementation Checklist

- [ ] Server defines tools with clear docstrings and typed parameters
- [ ] All tool inputs are validated before processing
- [ ] Error responses use a consistent JSON format
- [ ] Path-based tools prevent directory traversal
- [ ] Subprocess calls use allowlists (no `shell=True`)
- [ ] Secrets are loaded from environment variables, never hardcoded
- [ ] Tests cover tool discovery, execution, and error paths
- [ ] Transport type matches deployment model (stdio for local, HTTP for remote)
- [ ] Timeouts are set on all external/blocking operations
- [ ] Server follows the recommended project structure
