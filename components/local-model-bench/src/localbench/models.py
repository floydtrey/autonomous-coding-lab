from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    messages: list[dict[str, str]]
    context_mode: str = "isolated"
    context_group: str | None = None
    tags: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Suite:
    id: str
    name: str
    cases: list[BenchmarkCase]
    source_path: Path
    source_sha256: str
    defaults: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    raw: dict[str, Any]
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    provider_total_seconds: float | None = None
    load_seconds: float | None = None
    prompt_eval_seconds: float | None = None
    generation_seconds: float | None = None
    finish_reason: str | None = None

