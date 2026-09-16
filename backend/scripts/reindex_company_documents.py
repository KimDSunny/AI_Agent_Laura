"""Regenerate gte-small embeddings for PLANET company RAG documents."""

import json

from app.services.supabase_service import create_admin_supabase_client


DOCUMENT_TITLES = {
    "PLANET 회사 소개서.md",
    "PLANET 조직도와 담당 업무.md",
    "2026 프로젝트 현황.md",
    "2026-09-14 팀별 주간 계획.md",
}


def main() -> None:
    client = create_admin_supabase_client()
    rows = (
        client.table("document_sections")
        .select("id,content,documents!inner(title)")
        .execute()
        .data
    )
    targets = [row for row in rows if row["documents"]["title"] in DOCUMENT_TITLES]

    for index, row in enumerate(targets, start=1):
        generated = client.functions.invoke(
            "generate-embedding",
            invoke_options={"body": {"text": row["content"]}},
        )
        if isinstance(generated, bytes):
            generated = json.loads(generated.decode("utf-8"))
        embedding = generated.get("embedding") if isinstance(generated, dict) else None
        if not embedding:
            raise RuntimeError(f"Embedding generation failed for section {row['id']}")

        (
            client.table("document_sections")
            .update({"embedding": embedding})
            .eq("id", row["id"])
            .execute()
        )
        print(f"[{index}/{len(targets)}] indexed section {row['id']}")

    print(f"Reindexed {len(targets)} company document sections.")


if __name__ == "__main__":
    main()
