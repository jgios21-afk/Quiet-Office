"""A scripted Strands Model used only in tests and offline demos. It does not think: given the
tool specs it is offered, it calls each tool once in order, then returns a one-line summary.
This lets the full agent event loop (tool registry, hooks, Graph) run without model credentials."""
from __future__ import annotations

import json
from typing import Any, AsyncIterable

from strands.models import Model


class ScriptedModel(Model):
    def __init__(self, tool_args: dict[str, dict[str, Any]] | None = None):
        self.tool_args = tool_args or {}
        self.calls = 0

    def update_config(self, **cfg): ...
    def get_config(self): return {}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kw):
        yield {"output": output_model()}

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kw) -> AsyncIterable[dict]:
        used = {c["toolUse"]["name"] for m in messages if m["role"] == "assistant" for c in m["content"] if "toolUse" in c}
        def runnable(t):
            required = t["inputSchema"]["json"].get("required", [])
            return t["name"] not in used and t["name"] != "resolve_decision" and all(r in self.tool_args.get(t["name"], {}) for r in required)
        pending = [t for t in (tool_specs or []) if runnable(t)]
        yield {"messageStart": {"role": "assistant"}}
        if pending:
            spec = pending[0]
            self.calls += 1
            args = self.tool_args.get(spec["name"], {})
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"t{self.calls}", "name": spec["name"]}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(args)}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockDelta": {"delta": {"text": f"Done: ran {len(used)} tools."}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        yield {"metadata": {"usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}, "metrics": {"latencyMs": 0}}}
