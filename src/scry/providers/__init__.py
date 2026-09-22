from __future__ import annotations

from scry.config import Config
from scry.providers.base import VlmProvider, VlmResult, image_block, is_transient, text_block  # noqa: F401
from scry.providers.cache import CallCache
from scry.run import Run


def get_provider(cfg: Config, run: Run) -> VlmProvider:
    if cfg.model.provider == "openai_compat":
        from scry.providers.openai_compat import OpenAICompatProvider

        if cfg.model.mode == "batch":
            raise ValueError('[model] provider = "openai_compat" has no batch mode')
        return OpenAICompatProvider(cfg.model, CallCache(run.cache_dir))
    from scry.providers.anthropic_ import AnthropicProvider

    return AnthropicProvider(cfg.model, CallCache(run.cache_dir))
