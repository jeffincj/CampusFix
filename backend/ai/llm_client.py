"""
One wrapper around the LLM provider. Everything else in the app calls
get_client().create(...) and never talks to the provider SDK directly.

Settings (from .env):
  LLM_PROVIDER   "anthropic" (Claude) or "none" (AI off -> the app falls back to the classifier)
  LLM_MODEL      e.g. claude-opus-5-5
  LLM_EFFORT     low | medium | high   (how much the model thinks; low is enough for classification)
  LLM_FALLBACKS  "default" -> if a request is declined by the model's safety checks, the API retries
                 it on a fallback model server-side; "off" to disable
  ANTHROPIC_API_KEY  read by the Anthropic SDK itself
  LLM_INPUT_COST_PER_MTOK / LLM_OUTPUT_COST_PER_MTOK  USD per million tokens, for the cost metric

Every call is logged in the llm_calls table (latency, tokens, cost, success).
"""
import logging
import os
import time
from dataclasses import dataclass, field
from decimal import Decimal

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """The LLM call failed (network, API error, refusal, ...). Callers fall back to non-LLM logic."""


class LLMUnavailable(LLMError):
    """No LLM is configured (LLM_PROVIDER=none or no API key)."""


@dataclass
class LLMReply:
    text: str  # all text blocks joined
    content: list = field(default_factory=list)  # raw content blocks (needed for tool use)
    stop_reason: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0

    @property
    def tool_calls(self):
        return [block for block in self.content if getattr(block, "type", None) == "tool_use"]


class LLMClient:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
        self.model = os.getenv("LLM_MODEL", "claude-opus-5-5")
        self.effort = os.getenv("LLM_EFFORT", "low")
        self.fallbacks = os.getenv("LLM_FALLBACKS", "default").lower()
        self.timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
        self.input_cost = Decimal(os.getenv("LLM_INPUT_COST_PER_MTOK", "4.00"))
        self.output_cost = Decimal(os.getenv("LLM_OUTPUT_COST_PER_MTOK", "20.00"))
        self._sdk = None

    @property
    def enabled(self):
        return self.provider == "anthropic" and bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))

    def _client(self):
        if self._sdk is None:
            import anthropic  # imported lazily so the app runs without it when AI is off

            self._sdk = anthropic.Anthropic(timeout=self.timeout, max_retries=2)
        return self._sdk

    def cost(self, input_tokens, output_tokens):
        return (self.input_cost * input_tokens + self.output_cost * output_tokens) / Decimal(1_000_000)

    def create(self, *, purpose, system, messages, tools=None, json_schema=None, max_tokens=4000, effort=None):
        """
        Send one request. json_schema -> the reply text is guaranteed JSON matching it
        (structured outputs). tools -> the model may ask to call them (function calling).
        """
        if not self.enabled:
            raise LLMUnavailable("No LLM configured (set LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY).")

        params = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
            "output_config": {"effort": effort or self.effort},
        }
        if json_schema:
            params["output_config"]["format"] = {"type": "json_schema", "schema": json_schema}
        if tools:
            params["tools"] = tools

        started = time.monotonic()
        try:
            response = self._send(params)
        except Exception as error:  # any SDK/network error: log it and let the caller fall back
            self._log(purpose, started, success=False, error=f"{type(error).__name__}: {error}")
            raise LLMError(str(error)) from error

        usage = response.usage
        reply = LLMReply(
            text="".join(block.text for block in response.content if getattr(block, "type", None) == "text"),
            content=list(response.content),
            stop_reason=response.stop_reason or "",
            model=response.model,
            input_tokens=usage.input_tokens or 0,
            output_tokens=usage.output_tokens or 0,
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        if reply.stop_reason == "refusal":
            self._log(purpose, started, reply=reply, success=False, error="refusal")
            raise LLMError("The model declined this request.")
        self._log(purpose, started, reply=reply)
        return reply

    def _send(self, params):
        client = self._client()
        if self.fallbacks == "default":
            # Server-side fallback: a declined request is retried on another model in the same call.
            return client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **params)
        return client.messages.create(**params)

    def _log(self, purpose, started, reply=None, success=True, error=""):
        from .models import LLMCallLog

        latency = int((time.monotonic() - started) * 1000)
        try:
            LLMCallLog.objects.create(
                purpose=purpose, provider=self.provider, model=(reply.model if reply else self.model),
                success=success, latency_ms=latency,
                input_tokens=reply.input_tokens if reply else 0, output_tokens=reply.output_tokens if reply else 0,
                cost_usd=self.cost(reply.input_tokens, reply.output_tokens) if reply else 0, error=error[:300],
            )
        except Exception:  # logging must never break the request
            logger.exception("Could not log LLM call")


_client = None


def get_client():
    """The shared LLM client (created on first use)."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
