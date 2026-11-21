import time
from typing import Any, Dict, List, Optional, Tuple
import litellm
from litellm.caching.caching import Cache
from litellm.exceptions import (
    APIConnectionError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
)

from .config import Settings


class AllProvidersUnavailableError(Exception):
    pass


def parse_simulate_header(header_val: Optional[str]) -> Dict[str, int]:
    if not header_val:
        return {}
    mapping: Dict[str, int] = {}
    for part in header_val.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if v in {"429", "500", "502", "503"}:
            mapping[k] = int(v)
    return mapping


class LLMGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        litellm.drop_params = True
        if settings.cache_enabled:
            litellm.cache = Cache(type="local")

    def complete(
        self,
        messages: List[Dict[str, str]],
        simulate_failure_header: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        start = time.perf_counter()

        simulated: Dict[str, int] = {}
        if self.settings.enable_failure_simulation and simulate_failure_header:
            simulated = parse_simulate_header(simulate_failure_header)

        if not self.settings.key_pool:
            raise AllProvidersUnavailableError("No keys configured")

        use_cache = self.settings.cache_enabled and not bool(simulated)
        fallback_attempts = 0

        for entry in self.settings.key_pool:
            if "*" in simulated or entry.key_id in simulated:
                fallback_attempts += 1
                continue

            try:
                kwargs: Dict[str, Any] = {
                    "model": self.settings.llm_model,
                    "messages": messages,
                    "api_key": entry.api_key,
                    "caching": use_cache,
                    "timeout": 60,
                    "num_retries": 0,
                    "reasoning_effort": "minimal",
                }
                if not use_cache:
                    kwargs["cache"] = {"no-cache": True}

                response = litellm.completion(**kwargs)
                latency_ms = int((time.perf_counter() - start) * 1000)

                is_cache_hit = bool(
                    getattr(response, "_hidden_params", {}).get("cache_hit", False)
                )
                reply = (response.choices[0].message.content or "").strip()
                usage = getattr(response, "usage", None)
                input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
                output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)

                metadata = {
                    "resolution_source": "LLM_CACHE" if is_cache_hit else "LIVE_INFERENCE",
                    "model": self.settings.llm_model,
                    "latency_ms": latency_ms,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "key_id": None if is_cache_hit else entry.key_id,
                    "fallback_attempts": 0 if is_cache_hit else fallback_attempts,
                }
                return reply, metadata

            except (
                RateLimitError,
                ServiceUnavailableError,
                InternalServerError,
                APIConnectionError,
            ) as exc:
                print(f"[{entry.key_id}] PROVIDER ERROR:", repr(exc))
                fallback_attempts += 1
                continue
            except Exception as exc:
                print(f"[{entry.key_id}] LLM ERROR:", repr(exc))
                fallback_attempts += 1
                continue

        raise AllProvidersUnavailableError("all providers unavailable")