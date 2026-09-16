create table if not exists public.google_calendar_connections (
  user_id uuid primary key references auth.users(id) on delete cascade,
  encrypted_credentials text not null check (char_length(encrypted_credentials) >= 80),
  scope text not null,
  connected_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists google_calendar_connections_set_updated_at
on public.google_calendar_connections;
create trigger google_calendar_connections_set_updated_at
before update on public.google_calendar_connections
for each row execute function private.set_updated_at();

alter table public.google_calendar_connections enable row level security;

-- OAuth 토큰은 브라우저의 Data API에서 읽거나 쓸 수 없다.
-- 백엔드의 service role만 이 테이블을 다루며 사용자 ID는 서버 세션에서 결정한다.
revoke all on public.google_calendar_connections from public, anon, authenticated;
grant select, insert, update, delete on public.google_calendar_connections to service_role;

alter table public.schedules
  add column if not exists calendar_provider text check (
    calendar_provider is null or calendar_provider in ('google')
  ),
  add column if not exists external_event_id text,
  add column if not exists external_event_url text;

create unique index if not exists schedules_google_event_id_idx
on public.schedules(external_event_id)
where external_event_id is not null;
