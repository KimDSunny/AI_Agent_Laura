import json
import re
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase_functions.errors import FunctionsError

from app.models.auth import ProfileResponse, ProfileUpsert
from app.models.chat import AgentAction, ChatRequest, ChatResponse, ConversationMessage, Source
from app.models.onboarding import OnboardingProgress
from app.models.team_chat import TeamMessage
from app.services.agent_service import DocumentReference
from app.services.auth_service import AuthenticatedUser
from app.services.supabase_service import (
    create_admin_supabase_client,
    create_user_supabase_client,
)


class SupabaseRepository:
    _TOPIC_TERMS = {
        "company": ("회사", "기업", "어떤회사", "하는일", "사업", "미션", "비전", "고객", "제품", "본사", "위치"),
        "history": ("연혁", "설립", "창립", "역사", "사업부문", "성장"),
        "organization": (
            "조직", "조직도", "담당", "업무", "책임", "누가", "누구", "대표", "팀장", "리드", "소속",
            "윤지호", "김서윤", "박도현", "이나경", "최민준", "정유진",
        ),
        "projects": ("프로젝트", "서비스", "개발중", "만드는", "진행", "출시", "로드맵", "laura", "로라", "orbit", "오빗", "compass", "컴퍼스"),
        "weekly_plan": ("주간", "이번주", "계획", "목표", "주요일정", "할일", "업무계획"),
        "benefits": ("복지", "규정", "근무", "재택", "식대", "지원금", "코어타임", "건강검진"),
        "development": ("개발환경", "환경설정", "설정법", "세팅", "저장소", "node", "python", "docker", "로컬"),
        "approval": ("휴가", "연차", "반차", "결재", "신청", "승인", "휴무"),
    }
    _TOPIC_STRUCTURE_HINTS = {
        "company": ("회사소개", "회사개요", "미션비전"),
        "history": ("연혁",),
        "organization": ("조직도", "조직운영", "담당업무"),
        "projects": ("프로젝트현황",),
        "weekly_plan": ("주간계획",),
        "benefits": ("복지및사내규정", "근무및복지"),
        "development": ("개발환경설정", "로컬개발환경"),
        "approval": ("휴가및결재", "휴가결재절차"),
    }

    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user
        self.client = create_user_supabase_client(user.access_token)

    def get_profile(self) -> ProfileResponse | None:
        rows = self._run(
            self.client.table("profiles")
            .select("user_id,employee_name,hire_date,team")
            .eq("user_id", str(self.user.user_id))
            .limit(1)
        ).data
        return ProfileResponse.model_validate(rows[0]) if rows else None

    def save_profile(self, profile: ProfileUpsert) -> ProfileResponse:
        payload = {
            "user_id": str(self.user.user_id),
            "employee_name": profile.employee_name.strip(),
            "hire_date": profile.hire_date.isoformat(),
            "team": profile.team,
        }
        rows = self._run(
            self.client.table("profiles").upsert(payload, on_conflict="user_id")
        ).data
        self._ensure_onboarding_tasks(profile.team)
        return ProfileResponse.model_validate(rows[0])

    def delete_profile(self) -> None:
        self._run(
            create_admin_supabase_client()
            .table("profiles")
            .delete()
            .eq("user_id", str(self.user.user_id))
        )

    def get_google_calendar_connection(self) -> dict[str, Any] | None:
        rows = self._run(
            create_admin_supabase_client()
            .table("google_calendar_connections")
            .select("user_id,encrypted_credentials,scope,connected_at,updated_at")
            .eq("user_id", str(self.user.user_id))
            .limit(1)
        ).data
        return rows[0] if rows else None

    def save_google_calendar_connection(
        self,
        encrypted_credentials: str,
        scope: str,
    ) -> None:
        self._run(
            create_admin_supabase_client()
            .table("google_calendar_connections")
            .upsert(
                {
                    "user_id": str(self.user.user_id),
                    "encrypted_credentials": encrypted_credentials,
                    "scope": scope,
                    "updated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                },
                on_conflict="user_id",
            )
        )

    def delete_google_calendar_connection(self) -> None:
        self._run(
            create_admin_supabase_client()
            .table("google_calendar_connections")
            .delete()
            .eq("user_id", str(self.user.user_id))
        )

    def search_documents(self, question: str, team: str) -> list[DocumentReference]:
        semantic_matches = self._semantic_search(question, team)
        rows = self._run(
            self.client.table("document_sections")
            .select("section_title,content,documents!inner(title,visibility_team)")
        ).data
        references = list(semantic_matches)
        for row in rows:
            document = row.get("documents") or {}
            visibility_team = document.get("visibility_team")
            if visibility_team not in (None, team):
                continue
            reference = DocumentReference(
                title=document.get("title", "회사 문서"),
                section=row.get("section_title") or "본문",
                content=row["content"],
            )
            if reference not in references:
                references.append(reference)

        return self._rerank(question, references)

    @classmethod
    def _rerank(
        cls,
        question: str,
        references: list[DocumentReference],
    ) -> list[DocumentReference]:
        """질문의 주제가 명확히 일치하는 근거만 남기는 보수적인 재정렬 단계."""
        normalized_question = cls._normalize(question)
        team_entities = ("기획팀", "개발팀", "디자인팀", "마케팅팀", "인사팀")
        person_entities = ("윤지호", "김서윤", "박도현", "이나경", "최민준", "정유진")
        project_entities = ("laura", "로라", "orbit", "오빗", "compass", "컴퍼스")
        query_topics = {
            topic
            for topic, terms in cls._TOPIC_TERMS.items()
            if any(cls._normalize(term) in normalized_question for term in terms)
        }
        if not query_topics:
            return []

        ranked: list[tuple[int, int, DocumentReference]] = []
        for original_rank, reference in enumerate(references):
            title_structure = cls._normalize(reference.title)
            section_structure = cls._normalize(reference.section)
            haystack = cls._normalize(
                f"{reference.title} {reference.section} {reference.content}"
            )
            # 본문에 우연히 같은 단어가 나온 문서보다 제목·섹션 주제가 맞는 문서를 우선한다.
            # 예: '프로젝트 우선순위'가 적힌 조직도보다 '프로젝트 현황' 문서가 먼저 와야 한다.
            score = sum(
                150
                for topic in query_topics
                if any(
                    cls._normalize(hint) in section_structure
                    for hint in cls._TOPIC_STRUCTURE_HINTS.get(topic, ())
                )
            )
            score += sum(
                40
                for topic in query_topics
                if any(
                    cls._normalize(hint) in title_structure
                    for hint in cls._TOPIC_STRUCTURE_HINTS.get(topic, ())
                )
            )
            # 질문과 문서 양쪽에 실제로 등장한 주제어만 점수에 반영한다.
            # 예: 휴가 질문에 '신청'이라는 단어만 있는 복지 문서가 선택되는 것을 막는다.
            score += sum(
                10
                for topic in query_topics
                for term in cls._TOPIC_TERMS[topic]
                if cls._normalize(term) in normalized_question
                and cls._normalize(term) in haystack
            )
            score += sum(
                5
                for token in cls._tokens(question)
                if len(token) >= 2 and token in haystack
            )
            score += sum(
                300
                for entity in team_entities
                if cls._normalize(entity) in normalized_question
                and cls._normalize(entity) in section_structure
            )
            score += sum(
                300
                for entity in project_entities
                if cls._normalize(entity) in normalized_question
                and cls._normalize(entity) in section_structure
            )
            score += sum(
                200
                for entity in person_entities
                if cls._normalize(entity) in normalized_question
                and cls._normalize(entity) in haystack
            )
            if score >= 10:
                ranked.append((score, -original_rank, reference))

        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        if not ranked:
            return []
        wants_broad_answer = any(
            keyword in normalized_question
            for keyword in ("전체", "모든", "각팀", "팀별", "조직도", "프로젝트들", "진행중인프로젝트")
        )
        if wants_broad_answer:
            return [item[2] for item in ranked[:6]]
        best_score = ranked[0][0]
        return [item[2] for item in ranked if item[0] >= best_score - 2][:5]

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^0-9a-zA-Z가-힣]", "", value).lower()

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {token.lower() for token in re.findall(r"[0-9a-zA-Z가-힣]+", value)}

    def _semantic_search(self, question: str, team: str) -> list[DocumentReference]:
        try:
            generated = self.client.functions.invoke(
                "generate-embedding",
                invoke_options={"body": {"text": question}},
            )
        except FunctionsError:
            # 임베딩 함수가 잠시 중단돼도 기본 키워드 검색으로 답할 수 있어야 해.
            return []
        if isinstance(generated, bytes):
            generated = json.loads(generated.decode("utf-8"))
        embedding = generated.get("embedding") if isinstance(generated, dict) else None
        if not embedding:
            return []
        rows = self._run(
            self.client.rpc(
                "match_document_sections",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.68,
                    "match_count": 5,
                    "filter_team": team,
                },
            )
        ).data
        return [
            DocumentReference(
                title=row["document_title"],
                section=row.get("section_title") or "본문",
                content=row["content"],
            )
            for row in rows
        ]

    def save_exchange(self, request: ChatRequest, response: ChatResponse) -> None:
        conversation = self._get_or_create_conversation(request.conversation_id, request.team)
        conversation_id = conversation["id"]
        self._run(
            self.client.table("messages").insert(
                {
                    "conversation_id": conversation_id,
                    "user_id": str(self.user.user_id),
                    "sender": "user",
                    "content": request.message,
                }
            )
        )

        action_id = None
        if response.action:
            action_id = response.action.id
            self._run(
                self.client.table("agent_actions").insert(
                    {
                        "id": action_id,
                        "user_id": str(self.user.user_id),
                        "conversation_id": conversation_id,
                        "action_type": response.action.type,
                        "title": response.action.title,
                        "payload": {
                            "detail": response.action.detail,
                            "schedule_title": response.action.schedule_title or "일정",
                            "starts_at": response.action.starts_at.isoformat()
                            if response.action.starts_at
                            else self._next_friday_at_two().isoformat(),
                            **response.action.parameters,
                        },
                        "status": response.action.status,
                    }
                )
            )

        self._run(
            self.client.table("messages").insert(
                {
                    "conversation_id": conversation_id,
                    "user_id": str(self.user.user_id),
                    "sender": "agent",
                    "content": response.text,
                    "sources": [source.model_dump() for source in response.sources],
                    "action_id": action_id,
                }
            )
        )
        self._run(
            self.client.table("conversations")
            .update({"updated_at": datetime.now(ZoneInfo("UTC")).isoformat()})
            .eq("id", conversation_id)
            .eq("user_id", str(self.user.user_id))
        )

    def get_conversation(self, client_key: str, team: str) -> list[ConversationMessage]:
        conversations = self._run(
            self.client.table("conversations")
            .select("id")
            .eq("user_id", str(self.user.user_id))
            .eq("client_key", client_key)
            .eq("team", team)
            .limit(1)
        ).data
        if not conversations:
            return []

        rows = self._run(
            self.client.table("messages")
            .select("id,sender,content,sources,created_at,action_id")
            .eq("conversation_id", conversations[0]["id"])
            .eq("user_id", str(self.user.user_id))
            .order("created_at")
            .order("id")
        ).data
        action_ids = [row["action_id"] for row in rows if row.get("action_id")]
        actions_by_id: dict[str, dict[str, Any]] = {}
        if action_ids:
            action_rows = self._run(
                self.client.table("agent_actions")
                .select("id,action_type,title,payload,status")
                .eq("user_id", str(self.user.user_id))
                .in_("id", action_ids)
            ).data
            actions_by_id = {str(action["id"]): action for action in action_rows}

        return [self._to_message(row, actions_by_id) for row in rows]

    def get_onboarding_progress(self, team: str) -> OnboardingProgress:
        tasks = self._run(
            self.client.table("onboarding_tasks").select("id,team")
        ).data
        task_ids = [task["id"] for task in tasks if task["team"] in (None, team)]
        if not task_ids:
            return OnboardingProgress(team=team, completed=0, total=0)
        rows = self._run(
            self.client.table("user_onboarding_tasks")
            .select("task_id,completed_at")
            .eq("user_id", str(self.user.user_id))
            .in_("task_id", task_ids)
        ).data
        completed = sum(1 for row in rows if row.get("completed_at"))
        return OnboardingProgress(team=team, completed=completed, total=len(task_ids))

    def get_team_messages(self, team: str) -> list[TeamMessage]:
        self._require_own_team(team)
        rows = self._run(
            self.client.table("team_chat_messages")
            .select("id,user_id,team,sender_name,content,created_at")
            .eq("team", team)
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(100)
        ).data
        rows.reverse()
        return [
            TeamMessage(
                id=str(row["id"]),
                team=row["team"],
                sender_name=row["sender_name"],
                content=row["content"],
                is_own=str(row["user_id"]) == str(self.user.user_id),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def send_team_message(self, team: str, content: str) -> TeamMessage:
        profile = self._require_own_team(team)
        rows = self._run(
            self.client.table("team_chat_messages").insert(
                {
                    "user_id": str(self.user.user_id),
                    "team": team,
                    "sender_name": profile.employee_name,
                    "content": content.strip(),
                }
            )
        ).data
        row = rows[0]
        return TeamMessage(
            id=str(row["id"]),
            team=row["team"],
            sender_name=row["sender_name"],
            content=row["content"],
            is_own=True,
            created_at=row["created_at"],
        )

    def _require_own_team(self, team: str) -> ProfileResponse:
        profile = self.get_profile()
        if profile is None or profile.team != team:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="소속 팀 채팅에만 참여할 수 있습니다.",
            )
        return profile

    def find_employee(self, name: str) -> dict[str, Any] | None:
        cleaned = name.strip()
        if not cleaned:
            return None
        rows = self._run(
            create_admin_supabase_client()
            .table("profiles")
            .select("employee_name,team")
            .eq("employee_name", cleaned)
            .limit(1)
        ).data
        return rows[0] if rows else None

    def find_onboarding_task(self, title: str, team: str) -> dict[str, Any] | None:
        normalized = self._normalize(title)
        rows = self._run(
            self.client.table("onboarding_tasks").select("id,title,team")
        ).data
        candidates = [row for row in rows if row["team"] in (None, team)]
        exact = next((row for row in candidates if self._normalize(row["title"]) == normalized), None)
        if exact:
            return exact
        return next(
            (
                row
                for row in candidates
                if normalized and (
                    normalized in self._normalize(row["title"])
                    or self._normalize(row["title"]) in normalized
                )
            ),
            None,
        )

    def action_requires_calendar(self, action_id: str) -> bool:
        return self._get_action(action_id)["action_type"] == "create_schedule"

    def execute_action(self, action_id: str) -> str:
        action = self._get_action(action_id)
        if action["status"] == "approved":
            return "이미 처리된 요청이야."
        self._update_action_status(action_id, "running")
        payload = action.get("payload") or {}
        try:
            if action["action_type"] == "update_checklist":
                completed_at = (
                    datetime.now(ZoneInfo("UTC")).isoformat()
                    if payload.get("completed")
                    else None
                )
                self._retry_once(
                    lambda: self._run(
                        self.client.table("user_onboarding_tasks")
                        .update({"completed_at": completed_at})
                        .eq("user_id", str(self.user.user_id))
                        .eq("task_id", payload["task_id"])
                    )
                )
                message = f"{payload.get('task_title', '체크리스트')} 항목을 {'완료' if payload.get('completed') else '미완료'} 처리했습니다."
            else:
                starts_at = datetime.fromisoformat(payload["starts_at"])
                from app.services.google_calendar_service import google_calendar_service

                google_event = self._retry_once(
                    lambda: google_calendar_service.create_event(
                        self,
                        title=payload.get("schedule_title", "일정"),
                        description=payload.get("detail"),
                        starts_at=starts_at,
                        ends_at=starts_at + timedelta(hours=1),
                        event_id=f"planet{action_id.replace('-', '')}",
                    )
                )
                self._run(
                    self.client.table("schedules").upsert(
                        {
                            "id": action_id,
                            "user_id": str(self.user.user_id),
                            "title": payload.get("schedule_title", "일정"),
                            "detail": payload.get("detail"),
                            "starts_at": payload["starts_at"],
                            "assignee": "AI Agent Laura",
                            "status": "scheduled",
                            "calendar_provider": "google",
                            "external_event_id": google_event.get("id"),
                            "external_event_url": google_event.get("htmlLink"),
                        },
                        on_conflict="id",
                    )
                )
                message = f"{payload.get('schedule_title', '일정')}을 Google Calendar에 등록했습니다."
            self._run(
                self.client.table("agent_actions")
                .update(
                    {
                        "status": "approved",
                        "executed_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                    }
                )
                .eq("id", action_id)
                .eq("user_id", str(self.user.user_id))
            )
        except Exception:
            self._update_action_status(action_id, "failed")
            raise
        return message

    def decline_action(self, action_id: str) -> str:
        action = self._get_action(action_id)
        self._update_action_status(action_id, "declined")
        return "일정 등록을 취소했습니다." if action["action_type"] == "create_schedule" else "체크리스트 변경을 취소했습니다."

    def _ensure_onboarding_tasks(self, team: str) -> None:
        tasks = self._run(
            self.client.table("onboarding_tasks").select("id,team")
        ).data
        assignments = [
            {"user_id": str(self.user.user_id), "task_id": task["id"]}
            for task in tasks
            if task["team"] in (None, team)
        ]
        if assignments:
            self._run(
                self.client.table("user_onboarding_tasks").upsert(
                    assignments,
                    on_conflict="user_id,task_id",
                    ignore_duplicates=True,
                )
            )

    def _get_or_create_conversation(self, client_key: str, team: str) -> dict[str, Any]:
        rows = self._run(
            self.client.table("conversations")
            .select("id")
            .eq("user_id", str(self.user.user_id))
            .eq("client_key", client_key)
            .eq("team", team)
            .limit(1)
        ).data
        if rows:
            return rows[0]
        created = self._run(
            self.client.table("conversations").insert(
                {
                    "user_id": str(self.user.user_id),
                    "client_key": client_key,
                    "team": team,
                    "title": f"{team} 대화",
                }
            )
        ).data
        return created[0]

    def _get_action(self, action_id: str) -> dict[str, Any]:
        rows = self._run(
            self.client.table("agent_actions")
            .select("id,action_type,payload,status")
            .eq("id", action_id)
            .eq("user_id", str(self.user.user_id))
            .limit(1)
        ).data
        if not rows:
            raise HTTPException(status_code=404, detail="실행할 업무를 찾을 수 없어.")
        return rows[0]

    @staticmethod
    def _retry_once(function: Any) -> Any:
        for attempt in range(2):
            try:
                return function()
            except Exception:
                if attempt == 1:
                    raise

    def _update_action_status(self, action_id: str, action_status: str) -> None:
        self._run(
            self.client.table("agent_actions")
            .update({"status": action_status})
            .eq("id", action_id)
            .eq("user_id", str(self.user.user_id))
        )

    @staticmethod
    def _to_message(
        row: dict[str, Any],
        actions_by_id: dict[str, dict[str, Any]],
    ) -> ConversationMessage:
        action_data = actions_by_id.get(str(row.get("action_id")))
        action = None
        if action_data:
            payload = action_data.get("payload") or {}
            action = AgentAction(
                id=str(action_data["id"]),
                type=action_data["action_type"],
                title=action_data["title"],
                detail=payload.get("detail", ""),
                schedule_title=payload.get("schedule_title"),
                starts_at=payload.get("starts_at"),
                parameters={
                    key: value
                    for key, value in payload.items()
                    if key not in {"detail", "schedule_title", "starts_at"}
                },
                status=action_data["status"],
            )
        return ConversationMessage(
            id=str(row["id"]),
            sender=row["sender"],
            text=row["content"],
            sources=[Source.model_validate(source) for source in row.get("sources") or []],
            action=action,
            created_at=row["created_at"],
        )

    @staticmethod
    def _next_friday_at_two() -> datetime:
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.hour >= 14:
            days_until_friday = 7
        return (now + timedelta(days=days_until_friday)).replace(
            hour=14,
            minute=0,
            second=0,
            microsecond=0,
        )

    @staticmethod
    def _run(query: Any) -> Any:
        try:
            return query.execute()
        except APIError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Supabase 데이터 처리 중 문제가 발생했습니다.",
            ) from error
