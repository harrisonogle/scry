from __future__ import annotations

from vt.config import Config
from vt.providers.base import VlmProvider, VlmResult, image_block, text_block  # noqa: F401
from vt.providers.cache import CallCache
from vt.run import Run


def get_provider(cfg: Config, run: Run) -> VlmProvider:
    from vt.providers.anthropic_ import AnthropicProvider

    return AnthropicProvider(cfg.model, CallCache(run.cache_dir))
