create table public.team_chat_messages (
  id bigint generated always as identity primary key,
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  team text not null check (
    team in ('개발팀', '인사팀', '마케팅팀', '디자인팀', '기획팀')
  ),
  sender_name text not null check (char_length(sender_name) between 1 and 50),
  content text not null check (char_length(content) between 1 and 2000),
  created_at timestamptz not null default now()
);

create index team_chat_messages_team_created_idx
on public.team_chat_messages(team, created_at desc, id desc);

alter table public.team_chat_messages enable row level security;

create policy team_chat_messages_select_own_team
on public.team_chat_messages
for select
to authenticated
using (
  exists (
    select 1
    from public.profiles as profile
    where profile.user_id = (select auth.uid())
      and profile.team = team_chat_messages.team
  )
);

create policy team_chat_messages_insert_own_team
on public.team_chat_messages
for insert
to authenticated
with check (
  user_id = (select auth.uid())
  and exists (
    select 1
    from public.profiles as profile
    where profile.user_id = (select auth.uid())
      and profile.team = team_chat_messages.team
      and profile.employee_name = team_chat_messages.sender_name
  )
);

revoke all on table public.team_chat_messages from anon, authenticated;
grant select, insert on table public.team_chat_messages to authenticated;
grant usage, select on sequence public.team_chat_messages_id_seq to authenticated;
