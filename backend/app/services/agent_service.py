import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections.abc import Awaitable, Callable
from typing import Any, TypedDict
from uuid import uuid4
from zoneinfo import ZoneInfo

from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.models.chat import AgentAction, ChatRequest, ChatResponse, Source


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentReference:
    title: str
    section: str
    content: str


class AgentState(TypedDict, total=False):
    request: ChatRequest
    repository: Any
    history: list[Any]
    tool_name: str | None
    tool_arguments: dict[str, Any]
    response: ChatResponse
    status_callback: Callable[[dict[str, str | None]], Awaitable[None]]


TOOL_DEFINITIONS = [
    {
        "type": "function", "name": "search_company_documents",
        "description": "회사 소개와 연혁, 조직도, 팀 리드와 구성원 역할, 담당 업무, 현재 프로젝트, 팀별 주간 계획, 복지/규정, 개발 환경, 휴가/결재 등 사내 문서를 검색한다. 특정 인물이 누구인지나 팀 리드를 묻는 질문도 이 도구를 사용한다.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "find_employee",
        "description": "정확한 이름으로 현재 가입된 임직원의 소속 팀만 조회한다. 인물의 역할, 담당 업무, 팀 리드가 누구인지 묻는 질문에는 사용하지 않는다.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "get_onboarding_progress",
        "description": "현재 사용자의 온보딩 완료 현황을 조회한다.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "update_checklist",
        "description": "온보딩 체크리스트 항목의 완료 여부를 변경한다. 실제 변경 전 사용자 승인이 필요하다.",
        "parameters": {"type": "object", "properties": {"task_title": {"type": "string"}, "completed": {"type": "boolean"}}, "required": ["task_title", "completed"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "create_schedule",
        "description": "Google Calendar 일정을 만든다. 날짜, 시간, 제목이 모두 확인된 경우에만 호출하며 실제 등록 전 사용자 승인이 필요하다.",
        "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "starts_at": {"type": "string", "description": "Asia/Seoul 기준 ISO 8601 시작 시각"}}, "required": ["title", "starts_at"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "get_current_projects",
        "description": "현재 진행 중인 회사 프로젝트를 조회한다.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
]


class AgentService:
    def __init__(self) -> None:
        self.force_fallback = False
        graph = StateGraph(AgentState)
        graph.add_node("plan", self._plan)
        graph.add_node("execute_tool", self._execute_tool)
        graph.add_edge(START, "plan")
        graph.add_conditional_edges(
            "plan", lambda state: "tools" if state.get("tool_name") else "done",
            {"tools": "execute_tool", "done": END},
        )
        graph.add_edge("execute_tool", END)
        self.graph = graph.compile()

    async def chat(
        self,
        request: ChatRequest,
        repository: Any | None = None,
        references: list[DocumentReference] | None = None,
        on_status: Callable[[dict[str, str | None]], Awaitable[None]] | None = None,
    ) -> ChatResponse:
        settings = get_settings()
        if self.force_fallback or not settings.openai_configured or repository is None:
            if on_status:
                await on_status({"phase": "thinking", "label": "요청 의도 분석 중", "tool": None})
            if references is None and repository is not None:
                references = await asyncio.to_thread(repository.search_documents, request.message, request.team)
            response = self._fallback_response(request, references or [])
            if on_status:
                if response.action:
                    await on_status({
                        "phase": "awaiting_approval",
                        "label": "사용자 승인 대기",
                        "tool": response.action.type,
                    })
                else:
                    await on_status({"phase": "answering", "label": "답변 작성 중", "tool": None})
            return response
        history = await asyncio.to_thread(repository.get_conversation, request.conversation_id, request.team)
        try:
            result = await self.graph.ainvoke({
                "request": request,
                "repository": repository,
                "history": history[-10:],
                "status_callback": on_status,
            })
            return result["response"]
        except Exception:
            logger.exception("LangGraph agent execution failed; using deterministic fallback")
            references = await asyncio.to_thread(repository.search_documents, request.message, request.team)
            return self._fallback_response(request, references)

    async def _plan(self, state: AgentState) -> AgentState:
        await self._emit_status(state, "thinking", "요청 의도 분석 중")
        request = state["request"]
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        messages = [
            {"role": "user" if item.sender == "user" else "assistant", "content": item.text}
            for item in state.get("history", [])
        ]
        messages.append({"role": "user", "content": request.message})
        instructions = f"""
너는 PLANET 사내 온보딩 AI Agent Laura다. 현재 시각은 {now.isoformat()}, 시간대는 Asia/Seoul이다.
사용자의 요청에 맞는 도구 하나를 선택하라. 상대 날짜는 현재 시각을 기준으로 ISO 8601로 계산한다.
- 사내 정보는 반드시 조회 도구로 확인하고 문서에 없는 내용은 추측하지 않는다.
- 팀 리드, 담당자, 특정 인물의 역할이나 소개는 search_company_documents를 사용한다. find_employee는 정확한 이름의 소속 팀만 확인할 때 사용한다.
- '그 프로젝트', '그 사람', '아까 말한 것' 같은 후속 질문은 직전 대화의 대상을 도구 인자에 구체적인 이름으로 풀어서 넣는다.
- 오늘, 내일, 이번 주/다음 주 요일 또는 요일만 말한 것도 유효한 날짜다. 요일만 말하면 가장 가까운 미래의 해당 요일로 계산하고 정확한 달력 날짜를 다시 묻지 않는다.
- 일정 생성에는 제목, 날짜, 시간이 모두 필요하다. 하나라도 없으면 도구를 호출하지 말고 이미 받은 정보는 되묻지 않으며 부족한 정보만 한국어로 재질문한다. 날짜는 가능하면 해석한 달력 날짜를 괄호로 확인해준다.
- 체크리스트 변경에는 항목명과 완료/미완료 의도가 모두 필요하다. 부족하면 재질문한다.
- 일반 인사나 기능 안내는 핵심 기능 3개 이내, 4문장 이내로 짧게 직접 답한다.
- 변경 도구의 실제 실행은 서버가 사용자 승인 뒤에만 처리한다.
""".strip()
        settings = get_settings()
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = None
        for attempt in range(2):
            try:
                response = await client.responses.create(
                    model=settings.openai_model, instructions=instructions, input=messages,
                    tools=TOOL_DEFINITIONS, tool_choice="auto", parallel_tool_calls=False,
                    store=False,
                    safety_identifier=hashlib.sha256(str(state["repository"].user.user_id).encode()).hexdigest(),
                )
                break
            except Exception:
                if attempt == 1:
                    raise
        call = next((item for item in response.output if item.type == "function_call"), None)
        if call is None:
            await self._emit_status(state, "answering", "답변 작성 중")
            text = response.output_text.strip() or "필요한 정보를 조금 더 알려줘."
            return {"tool_name": None, "response": ChatResponse(text=text, conversation_id=request.conversation_id)}
        await self._emit_status(
            state,
            "tool_selected",
            f"{self._tool_label(call.name)} 선택",
            call.name,
        )
        return {"tool_name": call.name, "tool_arguments": json.loads(call.arguments)}

    async def _execute_tool(self, state: AgentState) -> AgentState:
        name, arguments = state["tool_name"], state.get("tool_arguments", {})
        request, repository = state["request"], state["repository"]
        await self._emit_status(state, "tool_running", f"{self._tool_label(name)} 실행 중", name)
        if name == "create_schedule":
            try:
                starts_at = datetime.fromisoformat(arguments["starts_at"])
                if starts_at.tzinfo is None:
                    starts_at = starts_at.replace(tzinfo=ZoneInfo("Asia/Seoul"))
                if starts_at <= datetime.now(ZoneInfo("Asia/Seoul")):
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                return {"response": ChatResponse(text="등록할 날짜와 시간을 다시 알려줘.", conversation_id=request.conversation_id)}
            response = ChatResponse(
                text="Google Calendar에 등록할 일정을 확인했어. 아래 내용을 확인하고 승인해줘.",
                conversation_id=request.conversation_id,
                action=self._schedule_action(arguments.get("title", "일정"), starts_at),
            )
            await self._emit_status(state, "awaiting_approval", "사용자 승인 대기", name)
            return {"response": response}
        if name == "update_checklist":
            task = await self._retry_tool(repository.find_onboarding_task, arguments.get("task_title", ""), request.team)
            if task is None:
                return {"response": ChatResponse(text="확인할 수 없습니다", conversation_id=request.conversation_id)}
            completed = bool(arguments["completed"])
            verb = "완료" if completed else "미완료"
            action = AgentAction(
                id=str(uuid4()), type="update_checklist", title=f"{task['title']} {verb} 처리",
                detail=f"온보딩 체크리스트 '{task['title']}' 항목을 {verb} 상태로 변경",
                parameters={"task_id": task["id"], "task_title": task["title"], "completed": completed},
            )
            await self._emit_status(state, "awaiting_approval", "사용자 승인 대기", name)
            return {"response": ChatResponse(text="체크리스트 변경 내용을 확인했어. 아래 내용을 확인하고 승인해줘.", conversation_id=request.conversation_id, action=action)}
        if name == "get_onboarding_progress":
            progress = await self._retry_tool(repository.get_onboarding_progress, request.team)
            text = f"온보딩 체크리스트는 {progress.total}개 중 {progress.completed}개 완료했어. 진행률은 {progress.percentage}%야."
            return {"response": ChatResponse(text=text, conversation_id=request.conversation_id)}
        if name == "find_employee":
            employee = await self._retry_tool(repository.find_employee, arguments.get("name", ""))
            if employee:
                text = f"{employee['employee_name']} 님은 {employee['team']} 소속이에요."
                return {"response": ChatResponse(text=text, conversation_id=request.conversation_id)}
            references = await self._retry_tool(repository.search_documents, request.message, request.team)
            return {"response": await self._compose_grounded_answer(state, references)}
        query = "현재 프로젝트" if name == "get_current_projects" else arguments.get("query", request.message)
        query = self._contextualize_query(query, state.get("history", []), request.message)
        references = await self._retry_tool(repository.search_documents, query, request.team)
        return {"response": await self._compose_grounded_answer(state, references)}

    async def _compose_grounded_answer(
        self,
        state: AgentState,
        references: list[DocumentReference],
    ) -> ChatResponse:
        request = state["request"]
        if not references:
            return ChatResponse(text="확인할 수 없습니다", conversation_id=request.conversation_id)

        relative_release = self._relative_release_response(request, references)
        if relative_release:
            return relative_release

        history = [
            {"role": "user" if item.sender == "user" else "assistant", "content": item.text}
            for item in state.get("history", [])[-6:]
        ]
        evidence = [
            {"document": item.title, "section": item.section, "content": item.content}
            for item in references[:6]
        ]
        instructions = """
너는 PLANET 신입사원의 적응을 돕는 AI Agent Laura다. 제공된 사내 문서 근거만 사용해 현재 질문에 답한다.
- 질문이 요구한 정보부터 바로 답하고, 관련 없는 배경 설명은 빼라.
- 예/아니요로 답할 수 있는 질문은 첫 문장에서 원칙적인 답을 분명히 말하고 예외를 뒤에 설명한다.
- 간단한 사실 질문은 1문장, 일반 질문은 2~4문장으로 답한다.
- 기본 답변은 350자 이내로 쓴다. 여러 항목을 비교하거나 나열할 때만 최대 500자까지 허용한다.
- 3개 이상의 항목은 한 줄에 하나씩 '•' 불릿으로 정리한다.
- 사용자가 문장 수나 형식을 지정하면 반드시 따른다.
- 직전 대화의 '그 프로젝트', '그 사람' 같은 표현이 무엇을 가리키는지 문맥에 맞게 이어서 답한다.
- 오늘·다음 달 같은 상대 날짜는 current_datetime과 resolved_relative_period를 기준으로 정확히 계산한다. 범위 밖의 날짜를 다음 달이라고 표현하지 않는다.
- 근거에 없는 내용은 보완하거나 추측하지 말고 정확히 '확인할 수 없습니다'라고만 답한다.
- 자연스럽고 친절한 한국어 존댓말을 사용한다. 문서 제목이나 출처 표시는 본문에 넣지 않는다.
""".strip()
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        next_month_start = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        following_month_start = (next_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        input_data = {
            "current_datetime": now.isoformat(),
            "timezone": "Asia/Seoul",
            "resolved_relative_period": {
                "next_month_start": next_month_start.date().isoformat(),
                "next_month_end": (following_month_start - timedelta(days=1)).date().isoformat(),
            },
            "conversation": history,
            "question": request.message,
            "evidence": evidence,
        }
        settings = get_settings()
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        try:
            response = None
            for attempt in range(2):
                try:
                    response = await client.responses.create(
                        model=settings.openai_model,
                        instructions=instructions,
                        input=json.dumps(input_data, ensure_ascii=False),
                        max_output_tokens=600,
                        store=False,
                        safety_identifier=hashlib.sha256(str(state["repository"].user.user_id).encode()).hexdigest(),
                    )
                    break
                except Exception:
                    if attempt == 1:
                        raise
            text = response.output_text.strip()
            if not text:
                raise ValueError("empty grounded response")
        except Exception:
            logger.exception("Grounded answer composition failed; using extractive fallback")
            return self._grounded_response(request, references)

        sources = [
            Source(title=item.title, section=item.section, relevant_sentence=item.content)
            for item in references[:6]
        ]
        return ChatResponse(text=text, conversation_id=request.conversation_id, sources=sources)

    @staticmethod
    def _relative_release_response(
        request: ChatRequest,
        references: list[DocumentReference],
        now: datetime | None = None,
    ) -> ChatResponse | None:
        compact = request.message.replace(" ", "")
        if "다음달" not in compact or "출시" not in compact:
            return None

        current = now or datetime.now(ZoneInfo("Asia/Seoul"))
        next_month_start = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        following_month_start = (next_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        release_dates: list[tuple[datetime, DocumentReference]] = []
        release_references: list[DocumentReference] = []

        for reference in references:
            if "출시" not in reference.content:
                continue
            release_references.append(reference)
            for sentence in re.split(r"(?<=[.!?])\s+", reference.content):
                if "출시" not in sentence:
                    continue
                for clause in re.split(r"[,，]", sentence):
                    if "출시" not in clause:
                        continue
                    for year_text, month_text, day_text in re.findall(
                        r"(?:(\d{4})년\s*)?(\d{1,2})월\s*(\d{1,2})일",
                        clause,
                    ):
                        month = int(month_text)
                        year = int(year_text) if year_text else current.year + (month < current.month)
                        try:
                            release_dates.append(
                                (current.replace(year=year, month=month, day=int(day_text)), reference)
                            )
                        except ValueError:
                            continue

        dates_in_next_month = [
            item for item in release_dates
            if next_month_start <= item[0] < following_month_start
        ]
        if dates_in_next_month:
            release_date, reference = min(dates_in_next_month, key=lambda item: item[0])
            text = f"네, {reference.section}의 출시 일정이 {release_date.month}월 {release_date.day}일로 확인돼요."
            selected_references = [reference]
        else:
            later_dates = [item for item in release_dates if item[0] >= following_month_start]
            if later_dates:
                release_date, reference = min(later_dates, key=lambda item: item[0])
                text = (
                    f"확인된 다음 달({next_month_start.month}월) 출시 일정은 없어요. "
                    f"가장 가까운 정식 출시는 {reference.section}의 {release_date.month}월 {release_date.day}일이에요."
                )
                selected_references = [reference]
            else:
                text = f"확인된 다음 달({next_month_start.month}월) 출시 일정은 없어요."
                selected_references = release_references[:1]

        sources = [
            Source(title=item.title, section=item.section, relevant_sentence=item.content)
            for item in selected_references
        ]
        return ChatResponse(text=text, conversation_id=request.conversation_id, sources=sources)

    @staticmethod
    def _contextualize_query(
        query: str,
        history: list[Any],
        current_question: str | None = None,
    ) -> str:
        question = current_question or query
        compact = question.replace(" ", "")
        if not any(word in compact for word in ("그프로젝트", "그사람", "그럼", "아까", "해당")):
            return query
        previous_user = next(
            (item.text for item in reversed(history) if item.sender == "user"),
            None,
        )
        return f"{previous_user}\n후속 질문: {question}" if previous_user else query

    @staticmethod
    async def _retry_tool(function: Any, *args: Any) -> Any:
        for attempt in range(2):
            try:
                return await asyncio.to_thread(function, *args)
            except Exception:
                if attempt == 1:
                    raise

    @staticmethod
    async def _emit_status(
        state: AgentState,
        phase: str,
        label: str,
        tool_name: str | None = None,
    ) -> None:
        callback = state.get("status_callback")
        if callback:
            await callback({"phase": phase, "label": label, "tool": tool_name})

    @staticmethod
    def _tool_label(tool_name: str) -> str:
        return {
            "search_company_documents": "사내 문서 검색",
            "find_employee": "임직원 조회",
            "get_onboarding_progress": "온보딩 진행률 조회",
            "update_checklist": "체크리스트 변경",
            "create_schedule": "Google Calendar 일정 등록",
            "get_current_projects": "현재 프로젝트 조회",
        }.get(tool_name, "업무 도구")

    def _fallback_response(self, request: ChatRequest, references: list[DocumentReference]) -> ChatResponse:
        compact = request.message.replace(" ", "")
        if any(k in compact for k in ("일정", "교육", "캘린더", "미팅", "회의")) and any(k in compact for k in ("등록", "추가", "예약", "잡아")):
            schedule = self._parse_schedule(request.message)
            if schedule is None:
                return ChatResponse(text="일정을 등록하려면 날짜와 시간을 함께 알려줘. 예: 오늘 오후 3시에 미팅 등록해줘.", conversation_id=request.conversation_id)
            title, starts_at = schedule
            return ChatResponse(text="Google Calendar에 등록할 일정을 확인했어. 아래 내용을 확인하고 승인해줘.", conversation_id=request.conversation_id, action=self._schedule_action(title, starts_at))
        return self._grounded_response(request, references)

    @staticmethod
    def _grounded_response(request: ChatRequest, references: list[DocumentReference]) -> ChatResponse:
        if not references:
            return ChatResponse(text="확인할 수 없습니다", conversation_id=request.conversation_id)
        compact = request.message.replace(" ", "")
        wants_overview = any(
            keyword in compact
            for keyword in ("전체", "모든", "각팀", "팀별", "조직도", "프로젝트", "어떤회사", "회사소개")
        )
        selected = [references[0]]
        if wants_overview:
            selected = [
                reference
                for reference in references
                if reference.title == references[0].title
            ][:5]

        text = selected[0].content if len(selected) == 1 else "\n\n".join(
            f"[{reference.section}]\n{reference.content}" for reference in selected
        )
        sources = [
            Source(
                title=reference.title,
                section=reference.section,
                relevant_sentence=reference.content,
            )
            for reference in selected
        ]
        return ChatResponse(text=text, conversation_id=request.conversation_id, sources=sources)

    @staticmethod
    def _schedule_action(title: str, starts_at: datetime) -> AgentAction:
        meridiem, display_hour = ("오전" if starts_at.hour < 12 else "오후"), (starts_at.hour % 12 or 12)
        return AgentAction(
            id=str(uuid4()), title=f"{title} 일정 등록",
            detail=f"{starts_at:%Y-%m-%d} {meridiem} {display_hour}:{starts_at:%M} · {title} · Google Calendar",
            schedule_title=title, starts_at=starts_at,
            parameters={"schedule_title": title, "starts_at": starts_at.isoformat()},
        )

    @staticmethod
    def _parse_schedule(message: str) -> tuple[str, datetime] | None:
        now, compact = datetime.now(ZoneInfo("Asia/Seoul")), message.replace(" ", "")
        if "오늘" in compact:
            target_date = now.date()
        elif "내일" in compact:
            target_date = (now + timedelta(days=1)).date()
        else:
            weekdays = {"월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3, "금요일": 4, "토요일": 5, "일요일": 6}
            weekday = next((v for k, v in weekdays.items() if k in compact), None)
            if weekday is None:
                return None
            target_date = (now + timedelta(days=(weekday - now.weekday()) % 7)).date()
        match = re.search(r"(?:(오전|오후)\s*)?(\d{1,2})시(?:\s*(\d{1,2})분)?", message)
        if not match:
            return None
        meridiem, hour_text, minute_text = match.groups()
        hour, minute = int(hour_text), int(minute_text or 0)
        if (meridiem and not 1 <= hour <= 12) or (not meridiem and not 0 <= hour <= 23) or not 0 <= minute <= 59:
            return None
        if meridiem == "오후" and hour != 12: hour += 12
        if meridiem == "오전" and hour == 12: hour = 0
        starts_at = datetime.combine(target_date, datetime.min.time(), ZoneInfo("Asia/Seoul")).replace(hour=hour, minute=minute)
        if starts_at <= now:
            return None
        title = "보안 교육" if "보안교육" in compact else "미팅" if "미팅" in compact else "회의" if "회의" in compact else "교육" if "교육" in compact else "일정"
        return title, starts_at


agent_service = AgentService()
