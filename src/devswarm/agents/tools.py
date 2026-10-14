"""Tool registry, standard engineering tool implementations, and MCP compatibility."""

import inspect
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, get_type_hints
from devswarm.core.exceptions import AgentError
from devswarm.llm.models import ToolDefinition
from devswarm.sandbox.patcher import FilePatcher
from devswarm.sandbox.runner import SandboxRunner
from devswarm.sandbox.workspace import WorkspaceManager


@dataclass
class Tool:
    """Wrapper around an executable function with metadata and schema."""

    name: str
    description: str
    func: Callable[..., Coroutine[Any, Any, Any]]
    is_mutating: bool = False
    requires_approval: bool = False

    def to_definition(self) -> ToolDefinition:
        """Convert to ToolDefinition for LLM function calling."""
        sig = inspect.signature(self.func)
        type_hints = get_type_hints(self.func)

        properties: dict[str, Any] = {}
        required: list[str] = []

        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = type_hints.get(param_name, str)
            # Basic type mapping
            schema_type = "string"
            for py_type, json_type in type_map.items():
                if param_type is py_type or (hasattr(param_type, "__origin__") and param_type.__origin__ is py_type):
                    schema_type = json_type
                    break

            prop_def: dict[str, Any] = {"type": schema_type}
            if schema_type == "array":
                prop_def["items"] = {"type": "string"}

            properties[param_name] = prop_def

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        )

    def to_mcp_tool_schema(self) -> dict[str, Any]:
        """Export as standard Model Context Protocol (MCP) tool schema."""
        defn = self.to_definition()
        return {
            "name": defn.name,
            "description": defn.description,
            "inputSchema": defn.parameters,
        }


class ToolRegistry:
    """Catalog of tools available to agents."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        is_mutating: bool = False,
        requires_approval: bool = False,
    ) -> Callable:
        """Decorator to register an async tool function."""
        def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable:
            tool = Tool(
                name=name,
                description=description,
                func=func,
                is_mutating=is_mutating,
                requires_approval=requires_approval,
            )
            self._tools[name] = tool
            return func

        return decorator

    def add_tool(self, tool: Tool) -> None:
        """Add an instantiated Tool object."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def get_definitions(self, tool_names: list[str] | None = None) -> list[ToolDefinition]:
        """Get LLM definitions for registered tools."""
        tools = self._tools.values() if tool_names is None else [self._tools[n] for n in tool_names if n in self._tools]
        return [t.to_definition() for t in tools]

    def export_mcp_tools(self) -> list[dict[str, Any]]:
        """Export all tools in standard MCP JSON format."""
        return [t.to_mcp_tool_schema() for t in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool with given arguments."""
        tool = self._tools.get(name)
        if not tool:
            raise AgentError(f"Tool '{name}' is not registered in this agent's catalog.")

        try:
            return await tool.func(**arguments)
        except Exception as exc:
            return f"Error executing tool '{name}': {exc}"


def create_standard_workspace_tools(
    workspace: WorkspaceManager,
    runner: SandboxRunner,
) -> ToolRegistry:
    """Construct standard software engineering tools connected to an isolated workspace."""
    registry = ToolRegistry()

    @registry.register(
        name="read_file",
        description="Read file contents from the workspace. Supports line offset and line limit.",
        is_mutating=False,
    )
    async def read_file(relative_path: str, offset_lines: int = 0, limit_lines: int | None = None) -> str:
        return workspace.read_file(relative_path, offset_lines=offset_lines, limit_lines=limit_lines)

    @registry.register(
        name="write_file",
        description="Write or overwrite a file in the workspace with complete content.",
        is_mutating=True,
    )
    async def write_file(relative_path: str, content: str, overwrite: bool = True) -> str:
        bytes_written = await workspace.write_file(relative_path, content, overwrite=overwrite)
        return f"Successfully wrote {bytes_written} bytes to {relative_path}"

    @registry.register(
        name="replace_content",
        description="Replace a unique target block of text in an existing file with replacement text.",
        is_mutating=True,
    )
    async def replace_content(
        relative_path: str,
        target: str,
        replacement: str,
        allow_multiple: bool = False,
    ) -> str:
        original = workspace.read_file(relative_path)
        modified = FilePatcher.replace_content(
            original,
            target,
            replacement,
            allow_multiple=allow_multiple,
        )
        await workspace.write_file(relative_path, modified, overwrite=True)
        diff = FilePatcher.generate_diff(original, modified, relative_path)
        stats = FilePatcher.calculate_stats(diff)
        return f"Replaced content in {relative_path} (+{stats['additions']}, -{stats['deletions']})"

    @registry.register(
        name="list_files",
        description="List files in a directory matching an optional glob pattern.",
        is_mutating=False,
    )
    async def list_files(relative_dir: str = ".", pattern: str = "*") -> list[str]:
        return workspace.list_files(relative_dir=relative_dir, pattern=pattern)

    @registry.register(
        name="search_code",
        description="Search for occurrences of a string or symbol across files in the workspace.",
        is_mutating=False,
    )
    async def search_code(query: str, extensions: list[str] | None = None) -> list[dict]:
        return workspace.search_code(query=query, extensions=extensions)

    @registry.register(
        name="get_tree",
        description="Get a structural directory tree of the workspace up to max_depth.",
        is_mutating=False,
    )
    async def get_tree(max_depth: int = 4) -> dict:
        return workspace.get_tree(max_depth=max_depth)

    @registry.register(
        name="execute_command",
        description="Execute a shell command (e.g. pytest, git status, linters) in the sandbox workspace.",
        is_mutating=True,
    )
    async def execute_command(command: str, timeout: float | None = None) -> dict:
        res = await runner.run(command=command, timeout=timeout)
        return {
            "command": res.command,
            "exit_code": res.exit_code,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "duration_seconds": res.duration_seconds,
            "timed_out": res.timed_out,
            "success": res.is_success,
        }

    return registry
