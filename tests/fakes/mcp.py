from __future__ import annotations


class FakeMcpClient:
    def __init__(self) -> None:
        self._tool_results: dict[str, str] = {}
        self.calls: list[tuple[str, str]] = []

    def seed_tool_result(self, tool_name: str, result: str) -> None:
        self._tool_results[tool_name] = result

    def call_tool(self, tool_name: str, query: str) -> str:
        self.calls.append((tool_name, query))
        return self._tool_results[tool_name]
