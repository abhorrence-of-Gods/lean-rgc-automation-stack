from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import os
import time
import urllib.error
import urllib.request

from ..schemas import stable_hash


SCHEMA_LLM_CALL = "lean-rgc-llm-call-v89.0"

PROVIDERS = ("mock", "replay", "openai_compatible", "anthropic")

ANTHROPIC_DEFAULT_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_API_VERSION = "2023-06-01"


@dataclass
class LLMClientConfig:
    provider: str = "replay"
    model: str = "mock-model"
    base_url: str | None = None
    # Only the env var name is ever stored or serialized; key values must
    # never reach boundary/episode artifacts.
    api_key_env: str = "LEAN_RGC_LLM_API_KEY"
    temperature: float = 0.2
    top_p: float = 0.95
    max_tokens: int = 2048
    seed: int | None = 0
    cache_dir: str = ".lean_rgc/llm_cache"
    ledger_path: str | None = None
    timeout_s: float = 120.0
    mock_responses: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str | Path) -> "LLMClientConfig":
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in obj.items() if k in known})


@dataclass
class LLMCompletion:
    text: str
    prompt_hash: str
    output_hash: str
    model_id: str
    model_version: str | None
    prompt_tokens: int
    completion_tokens: int
    cached: bool
    latency_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "prompt_hash": self.prompt_hash,
            "output_hash": self.output_hash,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "prompt_tokens": int(self.prompt_tokens),
            "completion_tokens": int(self.completion_tokens),
            "cached": bool(self.cached),
            "latency_seconds": float(self.latency_seconds),
        }


def _http_post_json(url: str, payload: dict[str, Any], headers: dict[str, str], *, timeout_s: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        request.add_header(key, value)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 529) and attempt < 2:
                time.sleep(2.0**attempt)
                last_error = exc
                continue
            raise
        except urllib.error.URLError as exc:
            if attempt < 2:
                time.sleep(2.0**attempt)
                last_error = exc
                continue
            raise
    raise RuntimeError(f"llm http retries exhausted: {last_error}")


class LLMClient:
    """Provider-agnostic completion client with a content-addressed cache.

    The cache key deliberately excludes the provider so replayed runs and
    local OpenAI-compatible servers can satisfy each other's lookups for the
    same (model, params, messages) tuple.
    """

    def __init__(self, config: LLMClientConfig):
        if config.provider not in PROVIDERS:
            raise ValueError(f"unknown llm provider: {config.provider}")
        self.config = config
        self._mock_call_index = 0

    def prompt_hash(self, *, system: str, user: str) -> str:
        cfg = self.config
        return stable_hash(
            {
                "model": cfg.model,
                "system": system,
                "user": user,
                "temperature": float(cfg.temperature),
                "top_p": float(cfg.top_p),
                "max_tokens": int(cfg.max_tokens),
                "seed": cfg.seed,
            },
            40,
        )

    def _cache_path(self, prompt_hash: str) -> Path:
        return Path(self.config.cache_dir) / f"{prompt_hash}.json"

    def _read_cache(self, prompt_hash: str) -> LLMCompletion | None:
        path = self._cache_path(prompt_hash)
        if not path.exists():
            return None
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return LLMCompletion(
            text=str(obj.get("text") or ""),
            prompt_hash=prompt_hash,
            output_hash=str(obj.get("output_hash") or ""),
            model_id=str(obj.get("model_id") or self.config.model),
            model_version=obj.get("model_version"),
            prompt_tokens=int(obj.get("prompt_tokens") or 0),
            completion_tokens=int(obj.get("completion_tokens") or 0),
            cached=True,
            latency_seconds=0.0,
        )

    def _write_cache(self, completion: LLMCompletion) -> None:
        path = self._cache_path(completion.prompt_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(completion.to_dict(), ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    def _ledger_append(self, completion: LLMCompletion) -> None:
        if not self.config.ledger_path:
            return
        row = {
            "schema_version": SCHEMA_LLM_CALL,
            "provider": self.config.provider,
            **completion.to_dict(),
            "created_at": float(time.time()),
        }
        row.pop("text", None)
        path = Path(self.config.ledger_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def _api_key(self) -> str:
        key = os.environ.get(self.config.api_key_env, "")
        if not key:
            raise RuntimeError(f"missing API key in env var {self.config.api_key_env}")
        return key

    def _complete_mock(self) -> tuple[str, str | None, int, int]:
        responses = self.config.mock_responses or ["{}"]
        text = responses[self._mock_call_index % len(responses)]
        self._mock_call_index += 1
        return text, "mock", 0, len(text.split())

    def _complete_openai_compatible(self, *, system: str, user: str) -> tuple[str, str | None, int, int]:
        cfg = self.config
        if not cfg.base_url:
            raise ValueError("openai_compatible provider requires base_url")
        payload: dict[str, Any] = {
            "model": cfg.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": float(cfg.temperature),
            "top_p": float(cfg.top_p),
            "max_tokens": int(cfg.max_tokens),
        }
        if cfg.seed is not None:
            payload["seed"] = int(cfg.seed)
        headers = {}
        key = os.environ.get(cfg.api_key_env, "")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        obj = _http_post_json(
            cfg.base_url.rstrip("/") + "/chat/completions", payload, headers, timeout_s=cfg.timeout_s
        )
        choices = obj.get("choices") or []
        text = str(((choices[0] if choices else {}).get("message") or {}).get("content") or "")
        usage = obj.get("usage") or {}
        return (
            text,
            str(obj.get("model") or cfg.model),
            int(usage.get("prompt_tokens") or 0),
            int(usage.get("completion_tokens") or 0),
        )

    def _complete_anthropic(self, *, system: str, user: str) -> tuple[str, str | None, int, int]:
        cfg = self.config
        payload: dict[str, Any] = {
            "model": cfg.model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "temperature": float(cfg.temperature),
            "top_p": float(cfg.top_p),
            "max_tokens": int(cfg.max_tokens),
        }
        headers = {
            "x-api-key": self._api_key(),
            "anthropic-version": ANTHROPIC_API_VERSION,
        }
        base = (cfg.base_url or ANTHROPIC_DEFAULT_BASE_URL).rstrip("/")
        obj = _http_post_json(base + "/v1/messages", payload, headers, timeout_s=cfg.timeout_s)
        blocks = obj.get("content") or []
        text = "".join(str(b.get("text") or "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
        usage = obj.get("usage") or {}
        return (
            text,
            str(obj.get("model") or cfg.model),
            int(usage.get("input_tokens") or 0),
            int(usage.get("output_tokens") or 0),
        )

    def complete(self, *, system: str, user: str) -> LLMCompletion:
        prompt_hash = self.prompt_hash(system=system, user=user)
        cached = self._read_cache(prompt_hash)
        if cached is not None:
            self._ledger_append(cached)
            return cached
        if self.config.provider == "replay":
            raise RuntimeError(f"replay provider cache miss for prompt_hash={prompt_hash}")
        start = time.monotonic()
        if self.config.provider == "mock":
            text, version, in_tokens, out_tokens = self._complete_mock()
        elif self.config.provider == "openai_compatible":
            text, version, in_tokens, out_tokens = self._complete_openai_compatible(system=system, user=user)
        else:
            text, version, in_tokens, out_tokens = self._complete_anthropic(system=system, user=user)
        completion = LLMCompletion(
            text=text,
            prompt_hash=prompt_hash,
            output_hash=stable_hash({"text": text}, 24),
            model_id=self.config.model,
            model_version=version,
            prompt_tokens=in_tokens,
            completion_tokens=out_tokens,
            cached=False,
            latency_seconds=float(time.monotonic() - start),
        )
        self._write_cache(completion)
        self._ledger_append(completion)
        return completion


__all__ = [
    "ANTHROPIC_API_VERSION",
    "ANTHROPIC_DEFAULT_BASE_URL",
    "LLMClient",
    "LLMClientConfig",
    "LLMCompletion",
    "PROVIDERS",
    "SCHEMA_LLM_CALL",
]
