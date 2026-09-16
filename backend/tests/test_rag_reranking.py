from app.services.agent_service import DocumentReference
from app.services.repository import SupabaseRepository


def test_project_question_prioritizes_project_document_over_organization_mention() -> None:
    references = [
        DocumentReference(
            title="PLANET 조직도와 담당 업무.md",
            section="기획팀",
            content=(
                "기획팀 리드는 김서윤입니다. 제품 전략, 고객 요구사항, 로드맵, "
                "지표 설계와 프로젝트 우선순위를 담당합니다."
            ),
        ),
        DocumentReference(
            title="2026 프로젝트 현황.md",
            section="Laura Onboarding Agent v1.0",
            content="Laura 프로젝트는 현재 고객 파일럿을 준비하고 있습니다.",
        ),
    ]

    ranked = SupabaseRepository._rerank("현재 어떤 프로젝트 진행중이야?", references)

    assert ranked[0].title == "2026 프로젝트 현황.md"


def test_weekly_plan_question_prioritizes_weekly_plan_document() -> None:
    references = [
        DocumentReference(
            title="PLANET 조직도와 담당 업무.md",
            section="개발팀",
            content="개발팀은 프로젝트 진행과 서비스 운영을 담당합니다.",
        ),
        DocumentReference(
            title="2026-09-14 팀별 주간 계획.md",
            section="개발팀 · 2026-09-14~18",
            content="개발팀의 이번 주 목표는 Laura 파일럿 안정성 확보입니다.",
        ),
    ]

    ranked = SupabaseRepository._rerank("개발팀 이번 주 계획 알려줘", references)

    assert ranked[0].title == "2026-09-14 팀별 주간 계획.md"


def test_company_overview_question_prioritizes_overview_section_over_history() -> None:
    references = [
        DocumentReference(
            title="PLANET 회사 소개서.md",
            section="회사 연혁",
            content="2024년 AI Agent 사업부와 Laura 연구 개발을 시작했습니다.",
        ),
        DocumentReference(
            title="PLANET 회사 소개서.md",
            section="회사 개요와 사업",
            content="PLANET은 신입사원의 빠른 적응을 돕는 B2B SaaS 회사입니다.",
        ),
    ]

    ranked = SupabaseRepository._rerank("PLANET은 어떤 회사야?", references)

    assert ranked[0].section == "회사 개요와 사업"


def test_named_person_question_can_retrieve_organization_document() -> None:
    references = [
        DocumentReference(
            title="PLANET 조직도와 담당 업무.md",
            section="기획팀",
            content="기획팀 리드는 김서윤이며 제품 전략과 로드맵을 담당합니다.",
        )
    ]

    ranked = SupabaseRepository._rerank("김서윤이 누구야?", references)

    assert ranked[0].section == "기획팀"


def test_named_team_question_prioritizes_exact_team_section() -> None:
    references = [
        DocumentReference(
            title="PLANET 조직도와 담당 업무.md",
            section="조직 운영 체계",
            content="PLANET은 기획팀, 개발팀, 디자인팀, 마케팅팀, 인사팀으로 운영합니다.",
        ),
        DocumentReference(
            title="PLANET 조직도와 담당 업무.md",
            section="개발팀",
            content="개발팀 리드는 박도현이며 AI Agent와 인프라를 담당합니다.",
        ),
    ]

    ranked = SupabaseRepository._rerank("개발팀은 무슨 일을 하고 팀 리드는 누구야?", references)

    assert [item.section for item in ranked] == ["개발팀"]


def test_named_project_question_prioritizes_exact_project_section() -> None:
    references = [
        DocumentReference(
            title="2026 프로젝트 현황.md",
            section="Laura Onboarding Agent v1.0",
            content="Laura는 온보딩 AI Agent 프로젝트입니다.",
        ),
        DocumentReference(
            title="2026 프로젝트 현황.md",
            section="Orbit Workspace Admin",
            content="Orbit은 온보딩 운영 허브 프로젝트입니다.",
        ),
    ]

    ranked = SupabaseRepository._rerank("Orbit 프로젝트 담당자는 누구야?", references)

    assert [item.section for item in ranked] == ["Orbit Workspace Admin"]
