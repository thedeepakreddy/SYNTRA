# Model Context Protocol (MCP) Integration Guide

SYNTRA incorporates native support for Anthropic / Linux Foundation **Model Context Protocol (MCP)** standards. SYNTRA can act both as an **MCP Tool Host** (consuming external MCP tools) and an **MCP Tool Provider** (exposing its engineering tools to external IDEs or agents).

---

## 1. Exporting SYNTRA Tools as MCP Schemas

Every tool registered in `ToolRegistry` implements `.to_mcp_tool_schema()`, producing a compliant Model Context Protocol tool schema:

```python
from syntra.agents.tools import create_standard_workspace_tools
from syntra.sandbox import WorkspaceManager, SandboxRunner

workspace = WorkspaceManager("/path/to/project")
runner = SandboxRunner("/path/to/project")
tools = create_standard_workspace_tools(workspace, runner)

# Export tools in MCP schema format
mcp_schemas = tools.export_mcp_tools()
for tool_schema in mcp_schemas:
    print(tool_schema["name"], tool_schema["inputSchema"])
```

### Standard Schema Example (`read_file`):
```json
{
  "name": "read_file",
  "description": "Read file contents from the workspace. Supports line offset and line limit.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "relative_path": { "type": "string" },
      "offset_lines": { "type": "integer" },
      "limit_lines": { "type": "integer" }
    },
    "required": ["relative_path"]
  }
}
```

---

## 2. Registering External MCP Tools into SYNTRA
Agents can be equipped with custom tools or bridge connections to remote MCP servers:

```python
from syntra.agents.tools import Tool, ToolRegistry

custom_registry = ToolRegistry()

@custom_registry.register(
    name="query_knowledge_base",
    description="Query enterprise semantic vector database",
    is_mutating=False,
)
async def query_knowledge_base(query: str, top_k: int = 5) -> list[str]:
    # Call remote MCP client / external service
    return ["Relevant documentation snippet..."]
```
