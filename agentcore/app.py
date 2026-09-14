"""Amazon Bedrock AgentCore Runtime entrypoint.

    pip install bedrock-agentcore bedrock-agentcore-starter-toolkit
    agentcore configure -e agentcore/app.py
    agentcore launch

Payloads:
  {"action": "daily"}                              -> run the background daily close, return the digest
  {"action": "ask", "request": "..."}              -> talk to the Office manager
  {"action": "decide", "decision_id": "...", "choice": "..."}
Schedule {"action": "daily"} nightly with EventBridge Scheduler to make the office fully unattended.
"""
from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from quiet_office.agents import build_office_manager
from quiet_office.daily import run_daily_close
from quiet_office.models import make_model
from quiet_office.tools.decisions import resolve_decision

app = BedrockAgentCoreApp()
_manager = None


@app.entrypoint
def invoke(payload: dict, context=None) -> dict:
    global _manager
    action = payload.get("action", "ask")
    if action == "daily":
        return {"digest": run_daily_close()}
    if action == "decide":
        return {"result": resolve_decision(decision_id=payload["decision_id"], choice=payload["choice"], note=payload.get("note", ""))}
    if _manager is None:
        _manager = build_office_manager(make_model())
    return {"result": str(_manager(payload.get("request", "What needs my attention?")))}


if __name__ == "__main__":
    app.run()
