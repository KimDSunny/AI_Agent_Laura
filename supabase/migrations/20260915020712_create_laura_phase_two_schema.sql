create schema if not exists private;

create extension if not exists vector with schema extensions;

create or replace function private.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

revoke all on schema private from public, anon, authenticated;
revoke all on function private.set_updated_at() from public, anon, authenticated;

create table public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  employee_name text not null check (char_length(employee_name) between 1 and 50),
  hire_date date not null,
  team text not null check (team in ('개발팀', '인사팀', '마케팅팀', '디자인팀', '기획팀')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  client_key text not null default 'default' check (char_length(client_key) between 1 and 100),
  team text not null check (team in ('개발팀', '인사팀', '마케팅팀', '디자인팀', '기획팀')),
  title text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, client_key, team)
);

create table public.messages (
  id bigint generated always as identity primary key,
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  sender text not null check (sender in ('user', 'agent')),
  content text not null check (char_length(content) between 1 and 10000),
  sources jsonb not null default '[]'::jsonb check (jsonb_typeof(sources) = 'array'),
  created_at timestamptz not null default now()
);

create table public.onboarding_tasks (
  id bigint generated always as identity primary key,
  team text check (team is null or team in ('개발팀', '인사팀', '마케팅팀', '디자인팀', '기획팀')),
  title text not null check (char_length(title) between 1 and 200),
  description text,
  sort_order integer not null default 0 check (sort_order >= 0),
  created_at timestamptz not null default now()
);

create table public.user_onboarding_tasks (
  id bigint generated always as identity primary key,
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  task_id bigint not null references public.onboarding_tasks(id) on delete cascade,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (user_id, task_id)
);

create table public.schedules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  title text not null check (char_length(title) between 1 and 200),
  detail text,
  starts_at timestamptz not null,
  assignee text,
  status text not null default 'scheduled' check (status in ('scheduled', 'completed', 'cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.documents (
  id bigint generated always as identity primary key,
  title text not null check (char_length(title) between 1 and 300),
  source_type text not null default 'text' check (source_type in ('text', 'pdf', 'url')),
  source_url text,
  visibility_team text check (
    visibility_team is null
    or visibility_team in ('개발팀', '인사팀', '마케팅팀', '디자인팀', '기획팀')
  ),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.document_sections (
  id bigint generated always as identity primary key,
  document_id bigint not null references public.documents(id) on delete cascade,
  section_title text,
  content text not null check (char_length(content) between 1 and 50000),
  embedding extensions.vector(384),
  metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object'),
  created_at timestamptz not null default now()
);

create table public.agent_actions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  conversation_id uuid references public.conversations(id) on delete set null,
  action_type text not null check (char_length(action_type) between 1 and 100),
  title text not null check (char_length(title) between 1 and 200),
  payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
  status text not null default 'pending' check (status in ('pending', 'running', 'approved', 'declined', 'failed')),
  requested_at timestamptz not null default now(),
  executed_at timestamptz
);

create index conversations_user_id_idx on public.conversations(user_id);
create index conversations_user_team_updated_idx on public.conversations(user_id, team, updated_at desc);
create index messages_conversation_created_idx on public.messages(conversation_id, created_at);
create index messages_user_id_idx on public.messages(user_id);
create index onboarding_tasks_team_sort_idx on public.onboarding_tasks(team, sort_order);
create index user_onboarding_tasks_user_id_idx on public.user_onboarding_tasks(user_id);
create index user_onboarding_tasks_task_id_idx on public.user_onboarding_tasks(task_id);
create index schedules_user_starts_idx on public.schedules(user_id, starts_at);
create index document_sections_document_id_idx on public.document_sections(document_id);
create index document_sections_embedding_hnsw_idx
  on public.document_sections
  using hnsw (embedding vector_cosine_ops)
  where embedding is not null;
create index agent_actions_user_requested_idx on public.agent_actions(user_id, requested_at desc);
create index agent_actions_conversation_id_idx on public.agent_actions(conversation_id);

create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function private.set_updated_at();

create trigger conversations_set_updated_at
before update on public.conversations
for each row execute function private.set_updated_at();

create trigger schedules_set_updated_at
before update on public.schedules
for each row execute function private.set_updated_at();

create trigger documents_set_updated_at
before update on public.documents
for each row execute function private.set_updated_at();

alter table public.profiles enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.onboarding_tasks enable row level security;
alter table public.user_onboarding_tasks enable row level security;
alter table public.schedules enable row level security;
alter table public.documents enable row level security;
alter table public.document_sections enable row level security;
alter table public.agent_actions enable row level security;

create policy profiles_select_own on public.profiles
for select to authenticated
using ((select auth.uid()) = user_id);

create policy profiles_insert_own on public.profiles
for insert to authenticated
with check ((select auth.uid()) = user_id);

create policy profiles_update_own on public.profiles
for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy conversations_select_own on public.conversations
for select to authenticated
using ((select auth.uid()) = user_id);

create policy conversations_insert_own on public.conversations
for insert to authenticated
with check ((select auth.uid()) = user_id);

create policy conversations_update_own on public.conversations
for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy conversations_delete_own on public.conversations
for delete to authenticated
using ((select auth.uid()) = user_id);

create policy messages_select_own on public.messages
for select to authenticated
using ((select auth.uid()) = user_id);

create policy messages_insert_own on public.messages
for insert to authenticated
with check (
  (select auth.uid()) = user_id
  and conversation_id in (
    select id from public.conversations where user_id = (select auth.uid())
  )
);

create policy onboarding_tasks_select_authenticated on public.onboarding_tasks
for select to authenticated
using (true);

create policy user_onboarding_tasks_select_own on public.user_onboarding_tasks
for select to authenticated
using ((select auth.uid()) = user_id);

create policy user_onboarding_tasks_insert_own on public.user_onboarding_tasks
for insert to authenticated
with check ((select auth.uid()) = user_id);

create policy user_onboarding_tasks_update_own on public.user_onboarding_tasks
for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy schedules_select_own on public.schedules
for select to authenticated
using ((select auth.uid()) = user_id);

create policy schedules_insert_own on public.schedules
for insert to authenticated
with check ((select auth.uid()) = user_id);

create policy schedules_update_own on public.schedules
for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy schedules_delete_own on public.schedules
for delete to authenticated
using ((select auth.uid()) = user_id);

create policy documents_select_authenticated on public.documents
for select to authenticated
using (true);

create policy document_sections_select_authenticated on public.document_sections
for select to authenticated
using (true);

create policy agent_actions_select_own on public.agent_actions
for select to authenticated
using ((select auth.uid()) = user_id);

create policy agent_actions_insert_own on public.agent_actions
for insert to authenticated
with check ((select auth.uid()) = user_id);

create policy agent_actions_update_own on public.agent_actions
for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;

grant usage on schema public to authenticated;
grant select, insert, update on public.profiles to authenticated;
grant select, insert, update, delete on public.conversations to authenticated;
grant select, insert on public.messages to authenticated;
grant select on public.onboarding_tasks to authenticated;
grant select, insert, update on public.user_onboarding_tasks to authenticated;
grant select, insert, update, delete on public.schedules to authenticated;
grant select on public.documents, public.document_sections to authenticated;
grant select, insert, update on public.agent_actions to authenticated;
grant usage, select on all sequences in schema public to authenticated;

create or replace function public.match_document_sections(
  query_embedding extensions.vector(384),
  match_threshold real default 0.70,
  match_count integer default 5,
  filter_team text default null
)
returns table (
  section_id bigint,
  document_id bigint,
  document_title text,
  section_title text,
  content text,
  similarity real
)
language sql
stable
security invoker
set search_path = ''
as $$
  select
    section.id,
    document.id,
    document.title,
    section.section_title,
    section.content,
    (1 - (section.embedding operator(extensions.<=>) query_embedding))::real as similarity
  from public.document_sections as section
  join public.documents as document on document.id = section.document_id
  where section.embedding is not null
    and (filter_team is null or document.visibility_team is null or document.visibility_team = filter_team)
    and 1 - (section.embedding operator(extensions.<=>) query_embedding) >= match_threshold
  order by section.embedding operator(extensions.<=>) query_embedding
  limit greatest(1, least(match_count, 20));
$$;

revoke all on function public.match_document_sections(extensions.vector, real, integer, text)
from public, anon;
grant execute on function public.match_document_sections(extensions.vector, real, integer, text)
to authenticated;

insert into public.onboarding_tasks (team, title, description, sort_order) values
  (null, '회사 소개 확인', '회사의 비전과 핵심 가치를 확인해요.', 10),
  (null, '조직도 확인', '함께 일할 조직과 담당자를 확인해요.', 20),
  (null, '보안 교육 수강', '필수 정보보안 교육을 완료해요.', 30),
  (null, '업무 도구 설정', '메일과 협업 도구 계정을 설정해요.', 40),
  (null, '사내 규정 확인', '근무와 복지 관련 규정을 확인해요.', 50),
  (null, '팀 온보딩 미팅', '팀원들과 첫 온보딩 미팅을 진행해요.', 60),
  (null, '현재 프로젝트 확인', '팀이 진행 중인 프로젝트 흐름을 확인해요.', 70),
  (null, '첫 주 회고 작성', '첫 주에 알게 된 내용과 질문을 정리해요.', 80);

insert into public.documents (title, source_type) values
  ('2026 프로젝트 현황.md', 'text'),
  ('회사 소개서.pdf', 'pdf');

insert into public.document_sections (document_id, section_title, content)
select id, '신규 서비스 개발 일정',
  '현재 신규 서비스 프로젝트는 개발 진행 단계이며, 다음 단계는 내부 테스트와 정식 출시 준비입니다.'
from public.documents where title = '2026 프로젝트 현황.md';

insert into public.document_sections (document_id, section_title, content)
select id, '연혁 · 2012–2026',
  '회사는 2012년에 설립됐고, 2024년에 AI 기반 신규 사업 부문을 만들었습니다.'
from public.documents where title = '회사 소개서.pdf';
