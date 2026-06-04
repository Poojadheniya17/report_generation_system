"""
Model client for the interpretation step.

`interpret()` takes an injected `model_call(system_prompt, user_message) -> str`
so the orchestration is testable without network or keys. This module provides
the real implementation backed by the Anthropic API, plus a tiny factory so the
rest of the app doesn't import the SDK directly.

The model is configurable (env: INTERPRETATION_MODEL) so we can move between
Claude models without code changes. The client's original spec used GPT; the
prompt is model-agnostic, and Claude runs it the same way.
"""
from __future__ import annotations

import os
from typing import Callable

# Defaults chosen for a long, strict-JSON generation. max_tokens is generous
# because the report has 5 domains x (3 facets + domain prose) + summary + recs.
DEFAULT_MODEL = os.environ.get("INTERPRETATION_MODEL", "claude-sonnet-4-6")
DEFAULT_MAX_TOKENS = int(os.environ.get("INTERPRETATION_MAX_TOKENS", "8000"))


def make_anthropic_model_call(
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> Callable[[str, str], str]:
    """
    Returns a model_call(system_prompt, user_message) -> str backed by Anthropic.
    Imports the SDK lazily so environments without it (e.g. unit tests) don't
    need it installed.
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set — required for live interpretation."
        )

    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic package not installed. Add 'anthropic' to requirements."
        ) from e

    client = anthropic.Anthropic(api_key=api_key)

    def _call(system_prompt: str, user_message: str) -> str:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        # concatenate text blocks
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )

    return _call
