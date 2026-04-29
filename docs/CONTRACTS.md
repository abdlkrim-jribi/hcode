# HCode Integration Contracts

> **Version**: 1.0
> **Last Updated**: 2026-04-29
> **Scope**: Merge agreement between `feature/agent-core-v1`, `feature/ui-ux-v1`, and `feature/mcp-v1`

---

## 1. Event Schema — `AgentEvent`

All inter-component communication flows through `AgentEvent`. Any change to this schema **MUST** be versioned.

```python
class AgentEvent:
    """
    Canonical event emitted by the agent core and consumed by UI/UX and extensions.
    """
    event_type: str          # e.g., "phase_change", "tool_call", "tool_result", "error", "message"
    phase: Optional[str]     # Current phase: "init", "planning", "execution", "verification", "fast"
    data: Dict[str, Any]     # Payload — schema depends on event_type
    timestamp: float         # Unix timestamp
    metadata: Dict[str, Any] # Optional context (session_id, tool_name, etc.)
```

### Event Types

| `event_type`     | `data` payload keys                                      | Emitter         | Consumer(s)      |
|------------------|----------------------------------------------------------|-----------------|------------------|
| `phase_change`   | `from_phase`, `to_phase`, `reason`                       | Orchestrator    | UI, Logger       |
| `tool_call`      | `tool_name`, `arguments`, `call_id`                      | Agent Loop      | UI, Logger       |
| `tool_result`    | `tool_name`, `call_id`, `result`, `success`, `duration`  | Tool Executor   | Agent Loop, UI   |
| `message`        | `role`, `content`, `model`                                | Agent           | UI               |
| `error`          | `error_type`, `message`, `traceback`, `recoverable`      | Any             | UI, Logger       |
| `token_update`   | `input_tokens`, `output_tokens`, `total_cost`            | Agent           | UI (token bar)   |
| `todo_update`    | `items`, `completed`, `total`                            | Todo Manager    | UI (todo bar)    |
| `mcp_status`     | `server_name`, `status`, `tools_count`                   | MCP Client      | UI, Logger       |

---

## 2. IPC Messages

### Agent → UI

| Message              | Payload                                        | When                        |
|----------------------|------------------------------------------------|-----------------------------|
| `AGENT_READY`        | `{ session_id, provider, model }`              | After init, before prompt   |
| `PHASE_STARTED`      | `{ phase, context }`                           | Phase handler begins        |
| `PHASE_COMPLETED`    | `{ phase, result, duration }`                  | Phase handler finishes      |
| `TOOL_EXECUTING`     | `{ tool_name, args }`                          | Before tool.execute()       |
| `TOOL_COMPLETED`     | `{ tool_name, result, success, duration }`     | After tool.execute()        |
| `STREAM_CHUNK`       | `{ content, is_final }`                        | During streaming response   |
| `ERROR`              | `{ type, message, recoverable }`               | On any error                |
| `SESSION_END`        | `{ reason, stats }`                            | On session termination      |

### UI → Agent

| Message              | Payload                                        | When                        |
|----------------------|------------------------------------------------|-----------------------------|
| `USER_INPUT`         | `{ content, mode }`                            | User submits prompt         |
| `USER_CONFIRM`       | `{ action, approved }`                         | Human-in-the-loop response  |
| `SESSION_ABORT`      | `{ reason }`                                   | User cancels session        |
| `MODE_SWITCH`        | `{ from_mode, to_mode }`                       | User switches fast/plan     |

---

## 3. Tool Interface Contract

All tools (native AND MCP-bridged) MUST implement `BaseTool`:

```python
class BaseTool(ABC):
    """Contract for all tools registered in ToolManager."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_description(self) -> str: ...

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]: ...

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult: ...

    def to_function_schema(self) -> Dict[str, Any]: ...

    def to_anthropic_tool_schema(self) -> Dict[str, Any]: ...
```

### ToolResult

```python
@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### ToolParameter

```python
@dataclass
class ToolParameter:
    name: str
    type: str           # "string", "integer", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None
```

---

## 4. MCP Bridge Contract

MCP tools are dynamically discovered at runtime. They are wrapped via `MCPToolBridge` to conform to `BaseTool`.

### Registration Flow

```
MCPConfigManager.list_servers()
  → MCPClientManager.connect_all()
    → MCPToolRegistry.register_all_mcp_tools()
      → ToolManager.register_tool(MCPToolBridge(...))
```

### MCP Config Schema (``.hcode/mcp_config.json``)

```json
{
  "servers": {
    "<server_name>": {
      "command": "<executable>",
      "args": ["<arg1>", "<arg2>"],
      "env": { "<KEY>": "<VALUE>" },
      "transport": "stdio" | "http",
      "enabled": true | false,
      "url": "<http_endpoint>"  // only for transport=http
    }
  }
}
```

---

## 5. Phase Lifecycle Contract

Phases execute in a defined order managed by `PhaseManager` and `AgentOrchestrator`.

### Phase Order

```
init → planning → execution → verification
        ↑           ↓
        └── (loop if verification fails)
```

### Fast Mode

```
fast (single-pass, no planning/verification)
```

### Phase Handler Interface

```python
class BasePhaseHandler(ABC):
    @abstractmethod
    async def execute(self, context: PhaseContext) -> PhaseResult: ...

    @abstractmethod
    def get_phase_name(self) -> str: ...
```

---

## 6. Breaking Change Policy

> **Rule**: NO breaking changes to the contracts above without:
> 1. Incrementing the contract version at the top of this file
> 2. Notifying ALL branch owners via PR comment or issue
> 3. Adding a migration note in this file under §7

---

## 7. Migration Notes

_None yet._

---

## 8. Branch Ownership

| Component       | Owner        | Branch                   |
|-----------------|--------------|--------------------------|
| UI/UX           | —            | `feature/ui-ux-v1`       |
| Agent Core      | Backend 1    | `feature/agent-core-v1`  |
| MCP / Extensions| Backend 2    | `feature/mcp-v1`         |
| Integration     | All          | `develop`                |
