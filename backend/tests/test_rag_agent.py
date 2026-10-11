"""Phase 6 tests: RAG (PDF ingest + search), the function-calling agent, chat + documents API."""
import io
import json
from types import SimpleNamespace

import pytest
from django.core.management import call_command

from ai import agent, rag
from ai.llm_client import LLMError, LLMReply
from ai.models import ChatHistory, Document, DocumentChunk
from complaints import services

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def rules():
    """The three sample rule PDFs, ingested."""
    call_command("ingest_documents", stdout=io.StringIO())
    return Document.objects.all()


def tool_call(name, args, call_id="t1"):
    block = SimpleNamespace(type="tool_use", id=call_id, name=name, input=args)
    return LLMReply(text="", content=[block], stop_reason="tool_use")


# --- RAG ------------------------------------------------------------------------

def test_chunking_with_overlap():
    text = "Rule one is here. " * 100
    chunks = rag.chunk_text(text, size=200, overlap=50)
    assert len(chunks) > 5
    assert all(len(c) <= 200 for c in chunks)
    assert chunks[0][-30:] in chunks[1]  # overlap keeps context


def test_ingest_sample_pdfs(rules):
    assert rules.count() == 3
    hostel = Document.objects.get(file_name="hostel_rules.pdf")
    assert hostel.pages == 2
    assert DocumentChunk.objects.filter(document=hostel, page=2).exists()


@pytest.mark.parametrize("question, file, page, phrase", [
    ("What time does the hostel gate close?", "hostel_rules.pdf", 1, "9:30 PM"),
    ("Can students keep an electric kettle in the room?", "hostel_rules.pdf", 2, "kettles"),
    ("minimum attendance to write the exam", "it_and_campus_policy.pdf", 2, "75 percent"),
    ("when do college buses leave", "it_and_campus_policy.pdf", 2, "4:45 PM"),
])
def test_search_finds_source_and_page(rules, question, file, page, phrase):
    top = rag.search(question, k=1)[0]
    assert (top["file"], top["page"]) == (file, page)
    assert phrase in top["text"]


def test_search_ignores_unrelated_questions(rules):
    assert rag.search("what is the weather today") == []


def test_search_with_no_documents():
    assert rag.search("anything") == []


# --- Tools are read-only and role-checked ------------------------------------------

@pytest.fixture
def complaints(student, hostel, it_dept):
    return [
        services.create_complaint(student, title="Fan", description="Fan broken in room", category="HOSTEL", block="B Block"),
        services.create_complaint(student, title="Wifi", description="Wifi down in library", category="IT", block="Library"),
        services.create_complaint(student, title="Wifi 2", description="Wifi slow in hostel", category="IT", urgency="high"),
    ]


def test_count_tool_respects_department(complaints, it_staff, admin_user):
    assert json.loads(agent.run_tool(it_staff, "count_complaints", {})[0])["total"] == 2
    result = json.loads(agent.run_tool(admin_user, "count_complaints", {"group_by": "category"})[0])
    assert result == {"total": 3, "groups": {"IT": 2, "HOSTEL": 1}}


def test_list_tool_filters_and_limits(complaints, admin_user):
    rows = json.loads(agent.run_tool(admin_user, "list_complaints", {"category": "IT", "urgency": "high", "limit": 50})[0])
    assert [r["title"] for r in rows] == ["Wifi 2"]


def test_get_complaint_hidden_from_other_department(complaints, it_staff):
    hostel_complaint = complaints[0]
    result = json.loads(agent.run_tool(it_staff, "get_complaint", {"id": hostel_complaint.id})[0])
    assert "error" in result


def test_bad_tool_input_is_reported_as_error(admin_user):
    text, is_error = agent.run_tool(admin_user, "list_complaints", {"status": "deleted"})
    assert is_error and "status must be one of" in text
    assert agent.run_tool(admin_user, "drop_table", {})[1] is True  # unknown tool


# --- The agent loop -----------------------------------------------------------------

def test_agent_calls_tool_then_answers(fake_llm, complaints, it_staff):
    llm = fake_llm([tool_call("count_complaints", {"status": "open"}),
                    LLMReply(text="There are 2 open IT complaints.", stop_reason="end_turn")])
    result = agent.run_chat(it_staff, "How many open complaints do we have?")
    assert result["answer"] == "There are 2 open IT complaints."
    assert result["tools_used"] == ["count_complaints"]

    second_call = llm.calls[1]["messages"]
    tool_result = second_call[-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["tool_use_id"] == "t1"
    assert json.loads(tool_result["content"]) == {"total": 2}  # computed with the IT staff's permissions
    assert {t["name"] for t in llm.calls[0]["tools"]} == set(agent.TOOL_FUNCTIONS)

    roles = list(ChatHistory.objects.values_list("role", flat=True))
    assert roles == ["user", "tool", "assistant"]


def test_agent_rag_answer_has_sources(fake_llm, rules, admin_user):
    fake_llm([tool_call("search_rules", {"query": "hostel gate closing time"}),
              LLMReply(text="Gates close at 9:30 PM on weekdays (hostel_rules.pdf, page 1).", stop_reason="end_turn")])
    result = agent.run_chat(admin_user, "What time do hostel gates close?")
    assert {"file": "hostel_rules.pdf", "page": 1} in result["sources"]
    assert ChatHistory.objects.filter(role="assistant").get().sources == result["sources"]


def test_off_topic_refused_without_calling_llm(fake_llm, admin_user):
    llm = fake_llm([])
    result = agent.run_chat(admin_user, "Write me a poem about the sea")
    assert result["refused"] and result["answer"] == agent.REFUSAL
    assert llm.calls == []
    assert ChatHistory.objects.filter(refused=True).count() == 1


def test_conversation_history_is_sent(fake_llm, complaints, admin_user):
    llm = fake_llm([LLMReply(text="3 complaints.", stop_reason="end_turn"), LLMReply(text="2 of them.", stop_reason="end_turn")])
    first = agent.run_chat(admin_user, "How many complaints are there?")
    agent.run_chat(admin_user, "How many of those are IT complaints?", session_id=first["session_id"])
    sent = llm.calls[1]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert sent[1]["content"] == "3 complaints."


def test_llm_down_falls_back_to_rag(fake_llm, rules, admin_user):
    fake_llm([LLMError("API down")])
    result = agent.run_chat(admin_user, "What is the rule about electric kettles in the hostel?")
    assert "not available" in result["answer"]
    assert {"file": "hostel_rules.pdf", "page": 2} in result["sources"]


def test_agent_stops_after_max_steps(fake_llm, admin_user):
    fake_llm([tool_call("top_hotspots", {}, call_id=f"t{i}") for i in range(agent.MAX_STEPS)])
    result = agent.run_chat(admin_user, "Show me the complaint hotspots")
    assert "could not finish" in result["answer"]


# --- API -----------------------------------------------------------------------------

def test_chat_api_roles(fake_llm, api_as, student, admin_user):
    fake_llm([LLMReply(text="Hello.", stop_reason="end_turn")])
    assert api_as(student).post("/api/chat/", {"message": "How many complaints?"}, format="json").status_code == 403
    response = api_as(admin_user).post("/api/chat/", {"message": "How many complaints?"}, format="json")
    assert response.status_code == 200 and response.data["answer"] == "Hello."
    history = api_as(admin_user).get(f"/api/chat/?session_id={response.data['session_id']}").data
    assert [m["role"] for m in history] == ["user", "assistant"]


def pdf_upload(name="rules.pdf"):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.conf import settings
    from pathlib import Path

    content = (Path(settings.BASE_DIR) / "data" / "rules" / "mess_rules.pdf").read_bytes()
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def test_admin_uploads_pdf(api_as, admin_user, hostel_staff):
    response = api_as(admin_user).post("/api/documents/", {"file": pdf_upload(), "title": "Mess policy"}, format="multipart")
    assert response.status_code == 201
    assert response.data["pages"] == 2 and response.data["chunks"] > 0
    assert rag.search("refund for missed meals", k=1)[0]["file"] == "rules.pdf"
    # staff can list but not upload
    assert len(api_as(hostel_staff).get("/api/documents/").data) == 1
    assert api_as(hostel_staff).post("/api/documents/", {"file": pdf_upload()}, format="multipart").status_code == 403


def test_upload_rejects_non_pdf(api_as, admin_user):
    from django.core.files.uploadedfile import SimpleUploadedFile

    fake = SimpleUploadedFile("evil.pdf", b"MZ not a pdf", content_type="application/pdf")
    response = api_as(admin_user).post("/api/documents/", {"file": fake}, format="multipart")
    assert response.status_code == 400 and Document.objects.count() == 0


def test_admin_deletes_document(api_as, admin_user, rules):
    document = rules.first()
    assert api_as(admin_user).delete(f"/api/documents/{document.id}/").status_code == 204
    assert not DocumentChunk.objects.filter(document_id=document.id).exists()
