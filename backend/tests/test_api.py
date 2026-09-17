from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.routes import health
from app.main import app


client = TestClient(app)


@pytest.mark.parametrize("supabase_configured", [False, True])
def test_health_check_reflects_supabase_configuration(
    monkeypatch: pytest.MonkeyPatch,
    supabase_configured: bool,
) -> None:
    monkeypatch.setattr(
        health,
        "get_settings",
        lambda: SimpleNamespace(
            app_name="PLANET Laura API",
            app_version="0.1.0",
            supabase_configured=supabase_configured,
        ),
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["supabase_configured"] is supabase_configured


def test_project_chat_returns_source() -> None:
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "현재 프로젝트를 알려줘",
            "team": "개발팀",
            "conversation_id": "project-test",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] == "project-test"
    assert body["sources"][0]["title"] == "2026 프로젝트 현황.md"
    assert body["sources"][0]["relevant_sentence"] in body["text"]
    assert len(body["sources"]) == 3


def test_semantic_chat_uses_top_document_without_exact_keyword() -> None:
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "지금 만드는 서비스는 앞으로 어떤 순서로 진행돼?",
            "team": "개발팀",
            "conversation_id": "semantic-test",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "고객 파일럿" in body["text"]
    assert body["sources"][0]["title"] == "2026 프로젝트 현황.md"


@pytest.mark.parametrize(
    ("question", "team", "expected_title"),
    [
        ("회사 설립 연혁을 알려줘", "인사팀", "PLANET 회사 소개서.md"),
        ("PLANET은 어떤 회사야?", "개발팀", "PLANET 회사 소개서.md"),
        ("조직별 담당 업무가 뭐야?", "기획팀", "PLANET 조직도와 담당 업무.md"),
        ("개발팀 이번 주 주간 계획을 알려줘", "개발팀", "2026-09-14 팀별 주간 계획.md"),
        ("재택근무 복지 규정이 궁금해", "마케팅팀", "복지 및 사내 규정.md"),
        ("로컬 개발 환경 설정법을 알려줘", "개발팀", "개발 환경 설정 가이드.md"),
        ("휴가 결재 신청 방법은?", "디자인팀", "휴가 및 결재 신청 안내.md"),
        ("휴가와 결재는 어떻게 신청해?", "개발팀", "휴가 및 결재 신청 안내.md"),
    ],
)
def test_company_document_categories_return_grounded_source(
    question: str,
    team: str,
    expected_title: str,
) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"message": question, "team": team, "conversation_id": "rag-categories"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sources"][0]["title"] == expected_title
    assert body["sources"][0]["relevant_sentence"] in body["text"]


def test_unknown_information_is_not_invented() -> None:
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "오늘 구내식당 점심 메뉴가 뭐야?",
            "team": "인사팀",
            "conversation_id": "unknown-rag",
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "확인할 수 없습니다"
    assert response.json()["sources"] == []


def test_team_restricted_document_is_not_returned() -> None:
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Node 로컬 개발 환경 설정법을 알려줘",
            "team": "인사팀",
            "conversation_id": "permission-rag",
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "확인할 수 없습니다"
    assert response.json()["sources"] == []


def test_blank_message_is_rejected() -> None:
    response = client.post(
        "/api/v1/chat",
        json={"message": "   ", "team": "개발팀"},
    )
    assert response.status_code == 422


def test_invalid_team_is_rejected() -> None:
    response = client.post(
        "/api/v1/chat",
        json={"message": "안녕", "team": "없는팀"},
    )
    assert response.status_code == 422


def test_schedule_action_requires_confirmation(fake_repository) -> None:
    fake_repository.google_calendar_connection = {"connected_at": "2026-09-15T00:00:00Z"}
    chat_response = client.post(
        "/api/v1/chat",
        json={
            "message": "금요일 오후 2시에 보안 교육 일정을 등록해줘",
            "team": "개발팀",
            "conversation_id": "action-test",
        },
    )
    action_id = chat_response.json()["action"]["id"]

    rejected = client.post(
        f"/api/v1/actions/{action_id}/execute",
        json={"confirmed": False},
    )
    assert rejected.status_code == 400

    approved = client.post(
        f"/api/v1/actions/{action_id}/execute",
        json={"confirmed": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_schedule_approval_starts_google_authorization_when_not_connected(
    fake_repository,
    monkeypatch,
) -> None:
    from app.api.routes import actions

    monkeypatch.setattr(
        actions.google_calendar_service,
        "authorization_url",
        lambda repository, resume_action_id=None: f"https://accounts.google.test/auth?action={resume_action_id}",
    )
    chat_response = client.post(
        "/api/v1/chat",
        json={
            "message": "내일 오후 3시에 미팅 등록해줘",
            "team": "개발팀",
            "conversation_id": "oauth-action-test",
        },
    )
    action_id = chat_response.json()["action"]["id"]

    response = client.post(
        f"/api/v1/actions/{action_id}/execute",
        json={"confirmed": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "authorization_required"
    assert response.json()["authorization_url"].endswith(action_id)
    assert fake_repository.actions[action_id].status == "pending"


def test_schedule_request_preserves_requested_time_and_title() -> None:
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "내일 오후 3시에 미팅 등록해줘",
            "team": "개발팀",
            "conversation_id": "schedule-fields-test",
        },
    )

    action = response.json()["action"]
    assert action["schedule_title"] == "미팅"
    assert action["starts_at"][11:16] == "15:00"


def test_schedule_request_asks_again_when_time_is_missing() -> None:
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "금요일에 보안 교육 일정 추가해줘",
            "team": "개발팀",
            "conversation_id": "schedule-clarification-test",
        },
    )

    assert response.json()["action"] is None
    assert response.json()["text"] == "일정을 등록할 시간을 알려주세요."


def test_checklist_action_does_not_require_google_calendar(fake_repository) -> None:
    from app.models.chat import AgentAction

    action = AgentAction(
        id="10000000-0000-0000-0000-000000000001",
        type="update_checklist",
        title="보안 교육 수강 완료 처리",
        detail="보안 교육 수강 항목을 완료 상태로 변경",
        parameters={"task_id": 3, "task_title": "보안 교육 수강", "completed": True},
    )
    fake_repository.actions[action.id] = action

    response = client.post(
        f"/api/v1/actions/{action.id}/execute",
        json={"confirmed": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert "완료 처리" in response.json()["message"]


def test_conversation_history() -> None:
    conversation_id = "history-test"
    client.post(
        "/api/v1/chat",
        json={
            "message": "회사 연혁을 알려줘",
            "team": "인사팀",
            "conversation_id": conversation_id,
        },
    )
    response = client.get(
        f"/api/v1/conversations/{conversation_id}",
        params={"team": "인사팀"},
    )
    assert response.status_code == 200
    assert len(response.json()["messages"]) == 2


def test_laura_direct_conversation_is_separate_from_team_chat() -> None:
    common = {"message": "회사 연혁을 알려줘", "team": "개발팀"}
    client.post(
        "/api/v1/chat",
        json={**common, "conversation_id": "planet-demo"},
    )
    client.post(
        "/api/v1/chat",
        json={**common, "conversation_id": "planet-laura"},
    )

    team_chat = client.get(
        "/api/v1/conversations/planet-demo", params={"team": "개발팀"}
    ).json()
    laura_chat = client.get(
        "/api/v1/conversations/planet-laura", params={"team": "개발팀"}
    ).json()

    assert len(team_chat["messages"]) == 2
    assert len(laura_chat["messages"]) == 2
    assert team_chat["conversation_id"] != laura_chat["conversation_id"]


def test_onboarding_progress() -> None:
    response = client.get("/api/v1/onboarding/progress", params={"team": "기획팀"})
    assert response.status_code == 200
    assert response.json() == {
        "team": "기획팀",
        "completed": 6,
        "total": 8,
        "percentage": 75,
    }


def test_profile_is_saved_and_loaded() -> None:
    saved = client.put(
        "/api/v1/profile",
        json={
            "employee_name": "김행성",
            "hire_date": "2026-09-15",
            "team": "개발팀",
        },
    )
    loaded = client.get("/api/v1/profile")

    assert saved.status_code == 200
    assert loaded.status_code == 200
    assert loaded.json()["employee_name"] == "김행성"
    assert loaded.json()["team"] == "개발팀"


def test_profile_reset_deletes_saved_user_state() -> None:
    client.put(
        "/api/v1/profile",
        json={
            "employee_name": "김행성",
            "hire_date": "2026-09-15",
            "team": "개발팀",
        },
    )

    deleted = client.delete("/api/v1/profile")
    loaded = client.get("/api/v1/profile")

    assert deleted.status_code == 204
    assert loaded.status_code == 200
    assert loaded.json() is None


def test_team_chat_is_human_message_storage_without_agent_response() -> None:
    client.put(
        "/api/v1/profile",
        json={"employee_name": "김행성", "hire_date": "2026-09-16", "team": "개발팀"},
    )

    sent = client.post(
        "/api/v1/team-chats/개발팀/messages",
        json={"content": "팀원 여러분 안녕하세요"},
    )
    loaded = client.get("/api/v1/team-chats/개발팀/messages")

    assert sent.status_code == 200
    assert sent.json()["sender_name"] == "김행성"
    assert sent.json()["content"] == "팀원 여러분 안녕하세요"
    assert loaded.json()["messages"] == [sent.json()]


def test_team_chat_rejects_other_team_access() -> None:
    client.put(
        "/api/v1/profile",
        json={"employee_name": "김행성", "hire_date": "2026-09-16", "team": "개발팀"},
    )

    response = client.post(
        "/api/v1/team-chats/인사팀/messages",
        json={"content": "다른 팀 메시지"},
    )

    assert response.status_code == 403


def test_google_calendar_status_reports_missing_server_configuration(monkeypatch) -> None:
    from app.api.routes import integrations

    monkeypatch.setattr(
        integrations.google_calendar_service,
        "status",
        lambda repository: {
            "configured": False,
            "connected": False,
            "connected_at": None,
        },
    )
    response = client.get("/api/v1/integrations/google-calendar/status")

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "connected": False,
        "connected_at": None,
    }


def test_chat_stream_emits_delta_and_done_events() -> None:
    response = client.post(
        "/api/v1/chat/stream",
        json={
            "message": "회사 연혁을 알려줘",
            "team": "인사팀",
            "conversation_id": "stream-test",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: status" in response.text
    assert "event: delta" in response.text
    assert "event: done" in response.text
