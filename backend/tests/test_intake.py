"""Phase 5 tests: LLM intake JSON validation, retry, fallback rules, and the LLM client."""
import json
from types import SimpleNamespace

import pytest

from ai import intake
from ai.llm_client import LLMClient, LLMError, LLMReply, LLMUnavailable
from ai.models import LLMCallLog

GOOD = {"category": "IT", "urgency": "high", "location": "Library",
        "summary": "No Wi-Fi in the library.", "language": "mixed"}


# --- JSON validation ------------------------------------------------------------

def test_valid_json_passes():
    assert intake.parse_and_validate(json.dumps(GOOD)) == GOOD


def test_code_fences_are_tolerated():
    assert intake.parse_and_validate(f"```json\n{json.dumps(GOOD)}\n```") == GOOD


@pytest.mark.parametrize("bad", [
    "not json at all",
    json.dumps({**GOOD, "category": "CANTEEN"}),  # not an allowed department
    json.dumps({**GOOD, "urgency": "extreme"}),
    json.dumps({k: v for k, v in GOOD.items() if k != "summary"}),  # missing field
    json.dumps({**GOOD, "extra": 1}),  # extra field
    json.dumps({**GOOD, "summary": "x" * 400}),  # too long
])
def test_invalid_json_rejected(bad):
    with pytest.raises(intake.IntakeError):
        intake.parse_and_validate(bad)


# --- extract(): retry and failure -------------------------------------------------

@pytest.mark.django_db
def test_extract_uses_schema_and_returns_data(fake_llm):
    llm = fake_llm([json.dumps(GOOD)])
    assert intake.extract("Library il wifi illa") == GOOD
    call = llm.calls[0]
    assert call["json_schema"] == intake.OUTPUT_SCHEMA  # structured output requested
    assert "<complaint>" in call["messages"][0]["content"]  # untrusted text is fenced


@pytest.mark.django_db
def test_extract_retries_once_then_succeeds(fake_llm):
    llm = fake_llm(["{broken", json.dumps(GOOD)])
    assert intake.extract("wifi down")["category"] == "IT"
    assert len(llm.calls) == 2
    assert "previous answer was invalid" in llm.calls[1]["messages"][0]["content"]


@pytest.mark.django_db
def test_extract_gives_up_after_one_retry(fake_llm):
    llm = fake_llm(["{broken", "still broken"])
    with pytest.raises(intake.IntakeError):
        intake.extract("wifi down")
    assert len(llm.calls) == 2


@pytest.mark.django_db
def test_extract_api_error_becomes_intake_error(fake_llm):
    fake_llm([LLMError("timeout")])
    with pytest.raises(intake.IntakeError):
        intake.extract("wifi down")


def test_extract_without_llm_raises():
    with pytest.raises(intake.IntakeError):
        intake.extract("wifi down")  # LLM_PROVIDER=none in tests


# --- Fallback rules ---------------------------------------------------------------

@pytest.mark.parametrize("text, language", [
    ("Wifi is not working in the library", "en"),
    ("விடுதியில் தண்ணீர் இல்லை", "ta"),
    ("ഹോസ്റ്റലിൽ വെള്ളമില്ല", "ml"),
    ("Room fan work aagala, romba heat ah iruku", "mixed"),
    ("Internet ரொம்ப slow ஆக இருக்கு", "mixed"),
])
def test_detect_language(text, language):
    assert intake.detect_language(text) == language


@pytest.mark.parametrize("text, urgency", [
    ("I got an electric shock from the switch", "critical"),
    ("Seniors are ragging first years", "critical"),
    ("No water in the bathroom since morning", "high"),
    ("Mess timing is too early", "low"),
    ("The food is a bit salty", "medium"),
])
def test_guess_urgency(text, urgency):
    assert intake.guess_urgency(text) == urgency


def test_rule_based_location():
    assert intake.rule_based_intake("fan broken in c block hostel")["location"] == "C Block Hostel"
    assert intake.rule_based_intake("fan broken", location_hint="Room 5")["location"] == "Room 5"


# --- LLMClient with a stubbed SDK -------------------------------------------------

def stub_sdk(stop_reason="end_turn", text='{"ok": true}', error=None):
    def create(**params):
        if error:
            raise error
        create.params = params
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason, model="claude-opus-5-5",
            usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
        )
    messages = SimpleNamespace(create=create)
    return SimpleNamespace(messages=messages, beta=SimpleNamespace(messages=messages)), create


@pytest.fixture
def llm_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("LLM_INPUT_COST_PER_MTOK", "4")
    monkeypatch.setenv("LLM_OUTPUT_COST_PER_MTOK", "20")
    return LLMClient()


@pytest.mark.django_db
def test_client_logs_latency_tokens_and_cost(llm_client):
    llm_client._sdk, create = stub_sdk()
    reply = llm_client.create(purpose="intake", system="s", messages=[{"role": "user", "content": "hi"}],
                              json_schema=intake.OUTPUT_SCHEMA)
    assert reply.text == '{"ok": true}'
    assert create.params["output_config"]["format"]["type"] == "json_schema"
    assert create.params["fallbacks"] == "default"  # server-side fallback on refusals
    log = LLMCallLog.objects.get()
    assert log.success and log.input_tokens == 1000 and log.output_tokens == 200
    assert float(log.cost_usd) == pytest.approx((1000 * 4 + 200 * 20) / 1_000_000)


@pytest.mark.django_db
def test_client_refusal_raises_and_logs(llm_client):
    llm_client._sdk, _ = stub_sdk(stop_reason="refusal", text="")
    with pytest.raises(LLMError):
        llm_client.create(purpose="intake", system="s", messages=[{"role": "user", "content": "hi"}])
    assert LLMCallLog.objects.get().error == "refusal"


@pytest.mark.django_db
def test_client_api_error_raises_and_logs(llm_client):
    llm_client._sdk, _ = stub_sdk(error=RuntimeError("connection reset"))
    with pytest.raises(LLMError):
        llm_client.create(purpose="chat", system="s", messages=[])
    assert not LLMCallLog.objects.get().success


def test_client_disabled_without_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(LLMUnavailable):
        LLMClient().create(purpose="x", system="s", messages=[])


def test_reply_tool_calls():
    block = SimpleNamespace(type="tool_use", name="count_complaints", input={}, id="t1")
    assert LLMReply(text="", content=[block]).tool_calls == [block]
