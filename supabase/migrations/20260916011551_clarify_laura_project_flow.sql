update public.document_sections
set content = content || ' 서비스의 앞으로 진행 순서는 사내 QA, 고객 파일럿, 안정화, 정식 출시입니다.',
    embedding = null
where document_id = (
  select id from public.documents where title = '2026 프로젝트 현황.md'
)
and section_title = 'Laura Onboarding Agent v1.0';
