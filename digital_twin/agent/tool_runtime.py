import json
from typing import Any, Dict

from digital_twin.mcp.mcp_server import LocalMCPServer, TOOLS


class AgentToolRuntime:
    """Protocol-neutral tool runtime for agent integrations."""

    def __init__(self) -> None:
        self._server = LocalMCPServer()

    @property
    def available_tool_names(self) -> set[str]:
        return {tool["name"] for tool in TOOLS}

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        response = self._server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }
        )
        if response is None:
            return {}
        if "error" in response:
            raise ValueError(response["error"]["message"])
        return json.loads(response["result"]["content"][0]["text"])
