"""Model provider factory. Default is Claude on Amazon Bedrock (what judges run);
QUIET_OFFICE_PROVIDER=anthropic|ollama switches providers without touching agent code."""
from __future__ import annotations

import os


def make_model():
    provider = os.environ.get("QUIET_OFFICE_PROVIDER", "bedrock").lower()
    if provider == "bedrock":
        from strands.models import BedrockModel
        return BedrockModel(model_id=os.environ.get("QUIET_OFFICE_MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
                            region_name=os.environ.get("AWS_REGION", "us-east-1"), temperature=0.2)
    if provider == "anthropic":
        from strands.models.anthropic import AnthropicModel
        return AnthropicModel(client_args={"api_key": os.environ["ANTHROPIC_API_KEY"]},
                              model_id=os.environ.get("QUIET_OFFICE_MODEL", "claude-sonnet-4-20250514"), max_tokens=2048)
    if provider == "ollama":
        from strands.models.ollama import OllamaModel
        return OllamaModel(host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
                           model_id=os.environ.get("QUIET_OFFICE_MODEL", "llama3.1"))
    if provider == "scripted":
        # Offline demo: a scripted model that calls each tool once. No reasoning, no credentials.
        import json, sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from tests.fake_model import ScriptedModel
        from .store import get_store
        outcomes = get_store().data["meta"].get("demo_outcomes", {})
        return ScriptedModel({"close_completed_events": {"outcomes_json": json.dumps(outcomes)}})
    raise ValueError(f"Unknown provider {provider}")
