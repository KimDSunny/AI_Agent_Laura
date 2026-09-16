-- 3단계: mock 사내 문서 RAG와 문서별 팀 권한

insert into public.documents (title, source_type, visibility_team)
select title, source_type, visibility_team
from (
  values
    ('PLANET 조직도와 담당 업무.md', 'text', null),
    ('복지 및 사내 규정.md', 'text', null),
    ('개발 환경 설정 가이드.md', 'text', '개발팀'),
    ('휴가 및 결재 신청 안내.md', 'text', null)
) as seed(title, source_type, visibility_team)
where not exists (
  select 1 from public.documents where documents.title = seed.title
);

update public.documents
set visibility_team = '개발팀'
where title = '2026 프로젝트 현황.md';

insert into public.document_sections (document_id, section_title, content, metadata)
select id, '조직별 담당 업무',
  'PLANET은 대표 직속의 기획팀, 개발팀, 디자인팀, 마케팅팀, 인사팀으로 구성됩니다. 기획팀은 제품 전략과 요구사항을, 개발팀은 제품 구현과 운영을, 디자인팀은 UX와 브랜드를, 마케팅팀은 캠페인과 고객 커뮤니케이션을, 인사팀은 채용·온보딩·조직문화를 담당합니다.',
  '{"topic":"organization"}'::jsonb
from public.documents
where title = 'PLANET 조직도와 담당 업무.md'
  and not exists (
    select 1 from public.document_sections
    where document_sections.document_id = documents.id
      and section_title = '조직별 담당 업무'
  );

insert into public.document_sections (document_id, section_title, content, metadata)
select id, '근무 및 복지',
  '근무시간은 오전 10시부터 오후 7시까지이며 코어타임은 오전 11시부터 오후 4시까지입니다. 월 2회 재택근무를 신청할 수 있고, 월 15만 원의 식대와 연 30만 원의 건강검진 비용을 지원합니다.',
  '{"topic":"benefits"}'::jsonb
from public.documents
where title = '복지 및 사내 규정.md'
  and not exists (
    select 1 from public.document_sections
    where document_sections.document_id = documents.id
      and section_title = '근무 및 복지'
  );

insert into public.document_sections (document_id, section_title, content, metadata)
select id, '로컬 개발 환경',
  '개발팀은 Node.js 22와 Python 3.13을 사용합니다. 사내 Git 저장소를 복제한 뒤 프론트엔드는 npm install, 백엔드는 uv sync를 실행하고, .env.example을 .env로 복사한 다음 Docker Compose로 로컬 서비스를 시작합니다.',
  '{"topic":"development"}'::jsonb
from public.documents
where title = '개발 환경 설정 가이드.md'
  and not exists (
    select 1 from public.document_sections
    where document_sections.document_id = documents.id
      and section_title = '로컬 개발 환경'
  );

insert into public.document_sections (document_id, section_title, content, metadata)
select id, '휴가·결재 절차',
  '휴가나 반차는 사용일 2영업일 전까지 사내 포털의 결재 메뉴에서 신청합니다. 결재선에 직속 팀장을 지정하고 사유와 기간을 입력한 뒤 제출하며, 팀장 승인 완료 후 휴가가 확정됩니다. 긴급 휴가는 먼저 팀장에게 알린 뒤 당일 신청할 수 있습니다.',
  '{"topic":"approval"}'::jsonb
from public.documents
where title = '휴가 및 결재 신청 안내.md'
  and not exists (
    select 1 from public.document_sections
    where document_sections.document_id = documents.id
      and section_title = '휴가·결재 절차'
  );

update public.document_sections
set metadata = metadata || '{"topic":"projects"}'::jsonb
where document_id = (
  select id from public.documents where title = '2026 프로젝트 현황.md'
);

update public.document_sections
set metadata = metadata || '{"topic":"history"}'::jsonb
where document_id = (
  select id from public.documents where title = '회사 소개서.pdf'
);

drop policy if exists documents_select_authenticated on public.documents;
drop policy if exists documents_select_by_team on public.documents;
create policy documents_select_by_team on public.documents
for select to authenticated
using (
  visibility_team is null
  or exists (
    select 1
    from public.profiles
    where profiles.user_id = (select auth.uid())
      and profiles.team = documents.visibility_team
  )
);

drop policy if exists document_sections_select_authenticated on public.document_sections;
drop policy if exists document_sections_select_by_document_permission on public.document_sections;
create policy document_sections_select_by_document_permission on public.document_sections
for select to authenticated
using (
  exists (
    select 1
    from public.documents
    where documents.id = document_sections.document_id
  )
);
