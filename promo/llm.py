"""
Provider-agnostic model layer.

One function, `complete()`. Everything that makes free-tier API work survivable
lives here so the pipeline stages stay readable:

  * swap provider/model by env var, CLI flag or UI dropdown - no code edits
  * disk cache keyed on (provider, model, system, prompt) - re-runs are free,
    instant and byte-identical, which is what makes a live demo safe
  * token-aware pacing for the measured 8,000 tokens/minute free-tier ceiling
  * 60s timeout, 2 retries, exponential backoff, honours Retry-After on 429
  * a hard cap on calls per run, printed as it goes
  * JSON-mode with a text fallback, because not every model supports it
  * every request and response written unedited to outputs/raw/

Measured Groq free-tier limits (from live response headers, 2026-11-08):
    x-ratelimit-limit-requests: 1000   per day
    x-ratelimit-limit-tokens:   8000   per minute   <- the binding constraint
"""
from __future__ import annotations

import os
import re
import json
import time
import hashlib
import threading

import requests

# ---------------------------------------------------------------------------
# Provider table. Adding a provider means adding a row, not changing logic.
# ---------------------------------------------------------------------------

PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "style": "openai",
        "default_model": "openai/gpt-oss-120b",
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "key_env": "OPENAI_API_KEY",
        "style": "openai",
        "default_model": "gpt-4o-mini",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "style": "openai",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "key_env": "GEMINI_API_KEY",
        "style": "gemini",
        "default_model": "gemini-3.5-flash-lite",
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "key_env": "ANTHROPIC_API_KEY",
        "style": "anthropic",
        "default_model": "claude-3-5-haiku-20241022",
    },
}

CACHE_DIR = ".cache"
RAW_DIR = "outputs/raw"


def load_dotenv(path: str = ".env") -> None:
    """Minimal .env reader. Avoids a dependency for four lines of work."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


# ---------------------------------------------------------------------------
# Token pacer
# ---------------------------------------------------------------------------

class TokenPacer:
    """
    Keeps a rolling 60-second record of tokens spent and sleeps before a
    request that would breach the per-minute ceiling.

    Reactive 429 handling alone is not enough on an 8,000 TPM budget: a
    50-episode run would spend most of its time in backoff. Pacing first and
    retrying second is noticeably faster.
    """

    def __init__(self, tokens_per_minute: int = 8000):
        self.tpm = tokens_per_minute
        self.events: list[tuple[float, int]] = []
        self.lock = threading.Lock()
        self.total_sleep = 0.0

    def _spent(self, now: float) -> int:
        self.events = [(t, n) for t, n in self.events if now - t < 60.0]
        return sum(n for _, n in self.events)

    def reserve(self, estimated: int) -> None:
        with self.lock:
            now = time.time()
            spent = self._spent(now)
            if spent + estimated > self.tpm and self.events:
                oldest = min(t for t, _ in self.events)
                wait = max(0.0, 60.0 - (now - oldest)) + 0.5
                if wait > 0:
                    print(f"[llm  ] pacing {wait:.1f}s "
                          f"({spent}+{estimated} would exceed {self.tpm} tok/min)")
                    time.sleep(wait)
                    self.total_sleep += wait
            self.events.append((time.time(), estimated))

    def record_actual(self, estimated: int, actual: int) -> None:
        with self.lock:
            if self.events:
                t, _ = self.events[-1]
                self.events[-1] = (t, max(actual, estimated))


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class LLM:
    """Stateful only in the ways that matter: call count, cache, pacing, log."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        max_calls: int = 400,
        use_cache: bool = True,
        tokens_per_minute: int = 8000,
        raw_dir: str = RAW_DIR,
    ):
        load_dotenv()
        self.provider = (provider or os.environ.get("LLM_PROVIDER") or "groq").lower()
        if self.provider not in PROVIDERS:
            raise ValueError(
                f"unknown provider {self.provider!r}; known: {sorted(PROVIDERS)}"
            )
        spec = PROVIDERS[self.provider]
        self.model = model or os.environ.get("LLM_MODEL") or spec["default_model"]
        self.spec = spec
        self.api_key = os.environ.get(spec["key_env"], "")
        self.max_calls = max_calls
        self.use_cache = use_cache
        self.pacer = TokenPacer(tokens_per_minute)
        self.raw_dir = raw_dir

        self.calls = 0
        self.cache_hits = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.failures: list[dict] = []
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(self.raw_dir, exist_ok=True)

    # -- plumbing ----------------------------------------------------------

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _cache_path(self, system: str, prompt: str, want_json: bool) -> str:
        key = f"{self.provider}|{self.model}|{int(want_json)}|{system}|{prompt}"
        return os.path.join(CACHE_DIR, hashlib.sha256(key.encode()).hexdigest() + ".json")

    def _build(self, system: str, prompt: str, want_json: bool, max_tokens: int) -> tuple[str, dict, dict]:
        style = self.spec["style"]
        if style == "openai":
            body = {
                "model": self.model,
                "temperature": 0,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            }
            if want_json:
                body["response_format"] = {"type": "json_object"}
            return (
                self.spec["url"],
                {"Authorization": f"Bearer {self.api_key}",
                 "Content-Type": "application/json"},
                body,
            )
        if style == "gemini":
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": system}]},
                "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens},
            }
            if want_json:
                body["generationConfig"]["responseMimeType"] = "application/json"
            return (
                self.spec["url"].format(model=self.model),
                {"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                body,
            )
        if style == "anthropic":
            return (
                self.spec["url"],
                {"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"},
                {"model": self.model, "max_tokens": max_tokens, "temperature": 0,
                 "system": system,
                 "messages": [{"role": "user", "content": prompt}]},
            )
        raise ValueError(f"unhandled provider style {style!r}")

    def _extract(self, payload: dict) -> tuple[str, int, int]:
        style = self.spec["style"]
        if style == "openai":
            usage = payload.get("usage") or {}
            return (
                payload["choices"][0]["message"]["content"] or "",
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
            )
        if style == "gemini":
            usage = payload.get("usageMetadata") or {}
            parts = payload["candidates"][0]["content"].get("parts", [])
            return (
                "".join(p.get("text", "") for p in parts),
                usage.get("promptTokenCount", 0),
                usage.get("candidatesTokenCount", 0),
            )
        if style == "anthropic":
            usage = payload.get("usage") or {}
            return (
                "".join(b.get("text", "") for b in payload.get("content", [])),
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
            )
        raise ValueError("unhandled style")

    # -- public ------------------------------------------------------------

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        want_json: bool = True,
        max_tokens: int = 900,
        tag: str = "call",
    ) -> dict | str | None:
        """
        Run one completion.

        Returns a dict when want_json, a str otherwise, or None if the call
        failed after retries. None is never silently replaced with a default;
        callers drop the candidate and the failure is logged.
        """
        cache_file = self._cache_path(system, prompt, want_json)
        if self.use_cache and os.path.exists(cache_file):
            self.cache_hits += 1
            cached = json.load(open(cache_file))
            return cached["parsed"]

        if not self.available:
            raise RuntimeError(
                f"{self.spec['key_env']} is not set. Use --no-llm for the "
                f"code-only pipeline, or put the key in .env"
            )
        if self.calls >= self.max_calls:
            raise RuntimeError(
                f"hard call cap reached ({self.max_calls}). Raise --max-calls "
                f"deliberately rather than by accident."
            )

        # ~4 chars per token is close enough to pace by. Reserve a realistic
        # completion size rather than the full max_tokens: these prompts ask
        # for a small JSON object, and reserving 1200 unused tokens on an
        # 8,000/minute budget cut the achievable rate roughly in half. The
        # actual usage from the response corrects the record afterwards.
        estimate = (len(system) + len(prompt)) // 4 + min(max_tokens, 400)
        text, raw_payload = None, None

        # `want_json` is the caller's contract and must not change. `ask_json`
        # is the wire setting, which we may drop to text mode mid-flight when
        # a model rejects structured output. Conflating the two returned a raw
        # string to a caller expecting a dict and crashed the ranking stage
        # at the very end of a 95-call run.
        ask_json = want_json
        forced_text = False

        for attempt in range(3):
            self.pacer.reserve(estimate)
            url, headers, body = self._build(system, prompt, ask_json, max_tokens)
            try:
                self.calls += 1
                response = requests.post(url, headers=headers, json=body, timeout=60)
            except requests.RequestException as exc:
                self._note_failure(tag, f"transport: {exc}", attempt)
                time.sleep(2 ** (attempt + 1))
                continue

            if response.status_code == 429:
                wait = float(response.headers.get("retry-after") or 2 ** (attempt + 2))
                print(f"[llm  ] 429 on {tag}; sleeping {wait:.1f}s")
                time.sleep(wait)
                continue

            if response.status_code == 400 and "json_validate_failed" in response.text:
                # The model accepted the request but could not emit valid JSON
                # inside the token budget. Retry in text mode and extract the
                # object ourselves. See docs/ai_mistakes_log.md #2.
                print(f"[llm  ] {self.model} failed JSON mode on {tag}; retrying as text")
                ask_json = False
                forced_text = True
                max_tokens = max(max_tokens, 1600)
                continue

            if response.status_code in (401, 403, 404):
                # Bad key, no access, or a model that doesn't exist. Retrying
                # cannot fix any of these, so fail immediately and loudly
                # rather than burning three attempts and 15 seconds.
                raise RuntimeError(
                    f"{self.provider}/{self.model}: HTTP {response.status_code} - "
                    f"{response.text[:200]}\nCheck LLM_MODEL and {self.spec['key_env']}."
                )

            if response.status_code != 200:
                self._note_failure(tag, f"HTTP {response.status_code}: {response.text[:300]}", attempt)
                time.sleep(2 ** (attempt + 1))
                continue

            raw_payload = response.json()
            text, n_in, n_out = self._extract(raw_payload)
            self.tokens_in += n_in
            self.tokens_out += n_out
            self.pacer.record_actual(estimate, n_in + n_out)

            # Reasoning models spend output tokens thinking before they write
            # anything. If the budget runs out first, the API returns HTTP 200
            # with empty content and finish_reason "length" - a success code
            # carrying no answer. Observed on gpt-oss-120b for the ranking
            # call: 1,600 tokens, 811 of them reasoning, zero content on one
            # run and a complete answer on the next. Diagnose it and buy more
            # room rather than reporting "unparseable JSON".
            finish = ""
            try:
                finish = raw_payload["choices"][0].get("finish_reason") or ""
            except (KeyError, IndexError, TypeError):
                pass
            if not (text or "").strip() and finish == "length" and attempt < 2:
                max_tokens *= 2
                estimate = (len(system) + len(prompt)) // 4 + min(max_tokens, 400)
                print(f"[llm  ] {tag}: empty answer, all {n_out} output tokens went to "
                      f"reasoning; retrying with max_tokens={max_tokens}")
                text = None
                continue
            break

        if text is None:
            self._note_failure(tag, "exhausted retries", 3)
            return None

        # Parse against the caller's contract, not the wire setting.
        parsed = _parse_json(text) if want_json else text
        if want_json and parsed is None:
            self._note_failure(
                tag,
                f"unparseable JSON{' (after text fallback)' if forced_text else ''}: "
                f"{text[:300]}",
                3,
            )
            return None

        self._dump_raw(tag, system, prompt, text, raw_payload)
        json.dump(
            {"provider": self.provider, "model": self.model, "tag": tag,
             "system": system, "prompt": prompt, "text": text, "parsed": parsed},
            open(cache_file, "w"), indent=2,
        )
        return parsed

    def _note_failure(self, tag: str, message: str, attempt: int) -> None:
        self.failures.append({"tag": tag, "attempt": attempt, "error": message,
                              "provider": self.provider, "model": self.model})
        print(f"[llm  ] FAIL {tag} attempt {attempt}: {message[:160]}")

    def _dump_raw(self, tag: str, system: str, prompt: str, text: str, payload) -> None:
        """Unedited request/response, which is a required deliverable."""
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", tag)[:80]
        stamp = f"{self.calls:04d}"
        path = os.path.join(self.raw_dir, f"{stamp}_{safe}.json")
        json.dump(
            {"provider": self.provider, "model": self.model, "tag": tag,
             "system": system, "prompt": prompt,
             "response_text": text, "response_payload": payload},
            open(path, "w"), indent=2, ensure_ascii=False,
        )

    def stats(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "calls": self.calls,
            "max_calls": self.max_calls,
            "cache_hits": self.cache_hits,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "paced_sleep_s": round(self.pacer.total_sleep, 1),
            "failures": len(self.failures),
            "failure_detail": self.failures[:20],
        }


def _parse_json(text: str) -> dict | None:
    """
    Parse a model response as JSON, tolerating the usual wrappers.

    Tries the whole string, then a ```json fence, then the outermost braces.
    """
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None
