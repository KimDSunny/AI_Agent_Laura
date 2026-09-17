import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.chat import ChatRequest
from app.services.agent_service import AgentService, DocumentReference


class PlannedAgent(AgentService):
    def __init__(self, tool_name: str, arguments: dict):
        self.tool_name = tool_name
        self.arguments = arguments
        super().__init__()

    async def _plan(self, state):
        return {"tool_name": self.tool_name, "tool_arguments": self.arguments}

    async def _compose_grounded_answer(self, state, references):
        return self._grounded_response(state["request"], references)


def test_langgraph_routes_document_search_to_grounded_answer(fake_repository):
    service = PlannedAgent("search_company_documents", {"query": "회사 연혁"})
    response = asyncio.run(
        service.chat(
            ChatRequest(message="회사 연혁 알려줘", team="인사팀", conversation_id="graph-rag"),
            repository=fake_repository,
        )
    )

    assert response.sources[0].title == "PLANET 회사 소개서.md"
    assert response.sources[0].relevant_sentence == response.text


def test_langgraph_schedule_tool_stops_for_approval(fake_repository):
    service = PlannedAgent(
        "create_schedule",
        {"title": "보안 교육", "starts_at": "2026-09-18T15:00:00+09:00"},
    )
    response = asyncio.run(
        service.chat(
            ChatRequest(message="금요일 오후 3시", team="개발팀", conversation_id="graph-schedule"),
            repository=fake_repository,
        )
    )

    assert response.action.type == "create_schedule"
    assert response.action.status == "pending"
    assert response.action.starts_at == datetime(2026, 9, 18, 15, 0, tzinfo=ZoneInfo("Asia/Seoul"))


def test_langgraph_checklist_tool_stops_for_approval(fake_repository):
    service = PlannedAgent(
        "update_checklist", {"task_title": "보안 교육", "completed": True}
    )
    response = asyncio.run(
        service.chat(
            ChatRequest(message="보안 교육 완료 처리해줘", team="개발팀", conversation_id="graph-checklist"),
            repository=fake_repository,
        )
    )

    assert response.action.type == "update_checklist"
    assert response.action.parameters == {
        "task_id": 3,
        "task_title": "보안 교육 수강",
        "completed": True,
    }


def test_tool_failure_is_retried_once():
    attempts = 0

    def flaky_tool():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary failure")
        return "ok"

    result = asyncio.run(AgentService._retry_tool(flaky_tool))

    assert result == "ok"
    assert attempts == 2


def test_langgraph_onboarding_progress_tool_returns_immediately(fake_repository):
    service = PlannedAgent("get_onboarding_progress", {})
    response = asyncio.run(
        service.chat(
            ChatRequest(message="온보딩 진행률 알려줘", team="기획팀", conversation_id="graph-progress"),
            repository=fake_repository,
        )
    )

    assert response.action is None
    assert "75%" in response.text


def test_langgraph_employee_lookup_returns_immediately(fake_repository):
    service = PlannedAgent("find_employee", {"name": "김행성"})
    response = asyncio.run(
        service.chat(
            ChatRequest(message="김행성 님 찾아줘", team="개발팀", conversation_id="graph-employee"),
            repository=fake_repository,
        )
    )

    assert response.action is None
    assert response.text == "김행성 님은 개발팀 소속입니다."


def test_missing_employee_lookup_falls_back_to_company_documents(fake_repository):
    service = PlannedAgent("find_employee", {"name": "김서윤"})
    response = asyncio.run(
        service.chat(
            ChatRequest(message="김서윤이 누구야?", team="개발팀", conversation_id="graph-person"),
            repository=fake_repository,
        )
    )

    assert response.text != "확인할 수 없습니다"
    assert response.sources[0].title == "PLANET 조직도와 담당 업무.md"


def test_follow_up_search_query_includes_previous_subject() -> None:
    history = [
        type("Message", (), {"sender": "user", "text": "Orbit이 뭐야?"})(),
        type("Message", (), {"sender": "agent", "text": "Orbit은 온보딩 운영 허브예요."})(),
    ]

    query = AgentService._contextualize_query(
        "Laura 프로젝트 담당자",
        history,
        "그 프로젝트 담당자는 누구야?",
    )

    assert "Orbit" in query
    assert "그 프로젝트 담당자는 누구야?" in query


def test_next_month_release_answer_uses_calendar_range() -> None:
    request = ChatRequest(
        message="다음 달 출시 일정이 있어?",
        team="개발팀",
        conversation_id="release-date",
    )
    references = [
        DocumentReference(
            title="2026 프로젝트 현황.md",
            section="Laura Onboarding Agent v1.0",
            content="9월 28일 파일럿을 시작하고 11월 2일 v1.0 정식 출시를 목표로 합니다.",
        )
    ]

    response = AgentService._relative_release_response(
        request,
        references,
        now=datetime(2026, 9, 16, 12, 0, tzinfo=ZoneInfo("Asia/Seoul")),
    )

    assert response.text == (
        "확인된 다음 달(10월) 출시 일정은 없습니다. "
        "가장 가까운 정식 출시는 Laura Onboarding Agent v1.0의 11월 2일입니다."
    )


def test_schedule_tool_rejects_time_inferred_by_model(fake_repository):
    service = PlannedAgent(
        "create_schedule",
        {"title": "팀 회의", "starts_at": "2026-09-18T00:00:00+09:00"},
    )

    response = asyncio.run(
        service.chat(
            ChatRequest(
                message="내일 팀 회의 일정 등록해줘",
                team="기획팀",
                conversation_id="missing-time",
            ),
            repository=fake_repository,
        )
    )

    assert response.action is None
    assert response.text == "일정을 등록할 시간을 알려주세요."


def test_schedule_clarification_uses_immediately_previous_request() -> None:
    history = [
        type("Message", (), {"sender": "user", "text": "내일 팀 회의 일정 등록해줘"})(),
        type("Message", (), {"sender": "agent", "text": "일정을 등록할 시간을 알려주세요."})(),
    ]

    context = AgentService._schedule_request_context("오후 3시", history)

    assert AgentService._missing_schedule_fields(context) == []


def test_plain_text_removes_markdown_emphasis() -> None:
    assert AgentService._plain_text("**Laura**는 `AI Agent`입니다.") == "Laura는 AI Agent입니다."


def test_unavailable_answer_accepts_terminal_punctuation() -> None:
    assert AgentService._is_unavailable_answer("확인할 수 없습니다.") is True


def test_unavailable_composed_answer_does_not_expose_irrelevant_source() -> None:
    request = ChatRequest(
        message="회사 옥상에 수영장이 있어?",
        team="기획팀",
        conversation_id="unknown-source",
    )
    references = [
        DocumentReference(
            title="복지 및 사내 규정.md",
            section="근무 및 복지",
            content="월 2회 재택근무를 신청할 수 있습니다.",
        )
    ]

    response = AgentService._composed_response(
        request,
        "확인할 수 없습니다.",
        references,
    )

    assert response.text == "확인할 수 없습니다"
    assert response.sources == []


def test_current_projects_intent_is_detected_without_model_judgment() -> None:
    assert AgentService._is_current_projects_question("현재 어떤 프로젝트를 진행하고 있어?") is True
    assert AgentService._is_current_projects_question("Laura 프로젝트 담당자는 누구야?") is False


def test_langgraph_current_projects_tool_returns_source(fake_repository):
    service = PlannedAgent("get_current_projects", {})
    response = asyncio.run(
        service.chat(
            ChatRequest(message="현재 프로젝트 알려줘", team="개발팀", conversation_id="graph-projects"),
            repository=fake_repository,
        )
    )

    assert response.action is None
    assert response.sources[0].title == "2026 프로젝트 현황.md"
    assert "Laura Onboarding Agent v1.0" in response.text
    assert "Orbit Workspace Admin" in response.text
    assert "Compass People Analytics" in response.text
