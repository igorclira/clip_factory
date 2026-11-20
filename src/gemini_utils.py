"""Shared Gemini client helpers: process-wide model-list caching and token usage logging."""

from __future__ import annotations

from typing import Any

_MODELS_CACHE: set[str] | None = None


def get_available_models(client: Any) -> set[str]:
    """Call client.models.list() at most once per process and return normalized model names."""
    global _MODELS_CACHE
    if _MODELS_CACHE is None:
        _MODELS_CACHE = {m.name.replace("models/", "") for m in client.models.list()}
    return set(_MODELS_CACHE)


def log_token_usage(label: str, model_name: str, resp: Any) -> None:
    """Print prompt/candidate token counts when resp.usage_metadata is present."""
    usage = getattr(resp, "usage_metadata", None)
    if not usage:
        return
    prompt_toks = getattr(usage, "prompt_token_count", None)
    cand_toks = getattr(usage, "candidates_token_count", None)
    total_toks = getattr(usage, "total_token_count", None)
    if prompt_toks is not None or cand_toks is not None:
        print(
            f"  [Usage] {label} ({model_name}): "
            f"prompt={prompt_toks} tokens, output={cand_toks} tokens, total={total_toks} tokens"
        )
