from collections import defaultdict
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.dependencies import get_repository
from app.main import app
from app.models.auth import ProfileResponse, ProfileUpsert
from app.models.chat import ChatRequest, ChatResponse, ConversationMessage
from app.models.onboarding import OnboardingProgress
from app.models.team_chat import TeamMessage
from app.services.agent_service import DocumentReference
from app.services.agent_service import agent_service
from app.services.repository import SupabaseRepository


class FakeRepository:
    def __init__(self) -> None:
        self.user = SimpleNamespace(user_id="00000000-0000-0000-0000-000000000001")
        self.profile = None
        self.conversations = defaultdict(list)
        self.actions = {}
        self.google_calendar_connection = None
        self.team_messages = defaultdict(list)

    def get_profile(self):
        return self.profile

    def save_profile(self, profile: ProfileUpsert):
        self.profile = ProfileResponse(
            user_id="00000000-0000-0000-0000-000000000001",
            **profile.model_dump(),
        )
        return self.profile

    def delete_profile(self):
        self.profile = None
        self.conversations.clear()
        self.actions.clear()
        self.team_messages.clear()

    def get_google_calendar_connection(self):
        return self.google_calendar_connection

    def save_google_calendar_connection(self, encrypted_credentials: str, scope: str):
        self.google_calendar_connection = {
            "encrypted_credentials": encrypted_credentials,
            "scope": scope,
            "connected_at": "2026-09-15T00:00:00Z",
        }

    def delete_google_calendar_connection(self):
        self.google_calendar_connection = None

    def search_documents(self, question: str, team: str):
        references = [
            DocumentReference(
                title="2026 프로젝트 현황.md",
                section="Laura Onboarding Agent v1.0",
                content="Laura 서비스의 앞으로 진행 순서는 사내 QA, 9월 28일 고객 파일럿, 안정화, 11월 2일 v1.0 정식 출시야.",
            ),
            DocumentReference(
                title="2026 프로젝트 현황.md",
                section="Orbit Workspace Admin",
                content="Orbit은 계정, 교육, 체크리스트와 결재 상태를 관리하며 12월 비공개 베타를 목표로 해.",
            ),
            DocumentReference(
                title="2026 프로젝트 현황.md",
                section="Compass People Analytics",
                content="Compass는 온보딩 이탈 구간과 반복 질문을 익명·집계 데이터로 분석하는 프로젝트야.",
            ),
            DocumentReference(
                title="PLANET 회사 소개서.md",
                section="회사 개요와 사업",
                content="PLANET은 신입사원의 빠른 적응을 돕는 Employee Experience OS를 만드는 서울 성수 기반 B2B SaaS 회사야.",
            ),
            DocumentReference(
                title="PLANET 회사 소개서.md",
                section="연혁 · 2012–2026",
                content="PLANET은 2012년에 설립됐고, 2024년에 AI Agent 사업부와 Laura 연구 개발을 시작했어.",
            ),
            DocumentReference(
                title="PLANET 조직도와 담당 업무.md",
                section="조직별 담당 업무",
                content="기획팀은 제품 전략, 개발팀은 구현과 운영, 디자인팀은 UX, 마케팅팀은 캠페인, 인사팀은 채용과 온보딩을 담당해.",
            ),
            DocumentReference(
                title="복지 및 사내 규정.md",
                section="근무 및 복지",
                content="코어타임은 오전 11시부터 오후 4시까지이고 월 2회 재택근무를 신청할 수 있어.",
            ),
            DocumentReference(
                title="휴가 및 결재 신청 안내.md",
                section="휴가·결재 절차",
                content="휴가는 사용일 2영업일 전까지 사내 포털에서 신청하고 직속 팀장의 승인을 받아야 해.",
            ),
            DocumentReference(
                title="2026-09-14 팀별 주간 계획.md",
                section=f"{team} · 2026-09-14~18",
                content=f"{team}의 이번 주 주간 계획과 목표, 담당자 및 완료 조건이 정리되어 있어.",
            ),
        ]
        if team == "개발팀":
            references.append(
                DocumentReference(
                    title="개발 환경 설정 가이드.md",
                    section="로컬 개발 환경",
                    content="Node.js 22와 Python 3.13을 설치하고 npm install과 uv sync를 실행해.",
                )
            )
        return SupabaseRepository._rerank(question, references)

    def save_exchange(self, request: ChatRequest, response: ChatResponse):
        key = (request.conversation_id, request.team)
        self.conversations[key].append(ConversationMessage(sender="user", text=request.message))
        self.conversations[key].append(
            ConversationMessage(
                sender="agent",
                text=response.text,
                sources=response.sources,
                action=response.action,
            )
        )
        if response.action:
            self.actions[response.action.id] = response.action

    def get_conversation(self, conversation_id: str, team: str):
        return list(self.conversations[(conversation_id, team)])

    def get_onboarding_progress(self, team: str):
        return OnboardingProgress(team=team, completed=6, total=8)

    def get_team_messages(self, team: str):
        self._require_team(team)
        return list(self.team_messages[team])

    def send_team_message(self, team: str, content: str):
        self._require_team(team)
        message = TeamMessage(
            id=str(len(self.team_messages[team]) + 1),
            team=team,
            sender_name=self.profile.employee_name,
            content=content.strip(),
            is_own=True,
            created_at=datetime.now(timezone.utc),
        )
        self.team_messages[team].append(message)
        return message

    def _require_team(self, team: str):
        if self.profile is None or self.profile.team != team:
            raise HTTPException(status_code=403, detail="소속 팀 채팅에만 참여할 수 있어.")

    def find_employee(self, name: str):
        if name == "김행성":
            return {"employee_name": "김행성", "team": "개발팀"}
        return None

    def find_onboarding_task(self, title: str, team: str):
        if "보안" in title:
            return {"id": 3, "title": "보안 교육 수강", "team": None}
        return None

    def action_requires_calendar(self, action_id: str):
        return self.actions[action_id].type == "create_schedule"

    def execute_action(self, action_id: str):
        self.actions[action_id].status = "approved"
        if self.actions[action_id].type == "update_checklist":
            return "보안 교육 수강 항목을 완료 처리했어."
        return "보안 교육 일정을 온보딩 체크리스트에 등록했습니다."

    def decline_action(self, action_id: str):
        self.actions[action_id].status = "declined"
        return "일정 등록을 취소했습니다."


@pytest.fixture(autouse=True)
def fake_repository():
    repository = FakeRepository()
    previous = agent_service.force_fallback
    agent_service.force_fallback = True
    app.dependency_overrides[get_repository] = lambda: repository
    yield repository
    agent_service.force_fallback = previous
    app.dependency_overrides.clear()
