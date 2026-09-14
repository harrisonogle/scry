from __future__ import annotations

from scry.config import Config
from scry.providers.base import VlmProvider, VlmResult, image_block, text_block  # noqa: F401
from scry.providers.cache import CallCache
from scry.run import Run


def get_provider(cfg: Config, run: Run) -> VlmProvider:
    from scry.providers.anthropic_ import AnthropicProvider

    return AnthropicProvider(cfg.model, CallCache(run.cache_dir))
