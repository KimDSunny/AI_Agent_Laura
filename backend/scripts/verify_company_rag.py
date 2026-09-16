"""Smoke-test semantic retrieval for the core PLANET company documents."""

import json

from app.services.agent_service import DocumentReference
from app.services.repository import SupabaseRepository
from app.services.supabase_service import create_admin_supabase_client


CASES = (
    ("PLANET은 어떤 회사야?", "개발팀", "PLANET 회사 소개서.md"),
    ("조직도와 팀별 담당 업무를 알려줘", "기획팀", "PLANET 조직도와 담당 업무.md"),
    ("현재 진행 중인 프로젝트를 알려줘", "마케팅팀", "2026 프로젝트 현황.md"),
    ("개발팀 이번 주 주간 계획은 뭐야?", "개발팀", "2026-09-14 팀별 주간 계획.md"),
)


def generate_embedding(client, text: str) -> list[float]:
    generated = client.functions.invoke(
        "generate-embedding",
        invoke_options={"body": {"text": text}},
    )
    if isinstance(generated, bytes):
        generated = json.loads(generated.decode("utf-8"))
    embedding = generated.get("embedding") if isinstance(generated, dict) else None
    if not embedding:
        raise RuntimeError(f"Embedding generation failed: {text}")
    return embedding


def main() -> None:
    client = create_admin_supabase_client()
    for question, team, expected_title in CASES:
        rows = client.rpc(
            "match_document_sections",
            {
                "query_embedding": generate_embedding(client, question),
                "match_threshold": 0.68,
                "match_count": 5,
                "filter_team": team,
            },
        ).execute().data
        references = [
            DocumentReference(
                title=row["document_title"],
                section=row.get("section_title") or "본문",
                content=row["content"],
            )
            for row in rows
        ]
        ranked = SupabaseRepository._rerank(question, references)
        titles = [reference.title for reference in ranked]
        if not titles or titles[0] != expected_title:
            raise AssertionError(f"{question!r}: expected {expected_title!r}, got {titles!r}")
        print(f"PASS {question} -> {expected_title}")


if __name__ == "__main__":
    main()
