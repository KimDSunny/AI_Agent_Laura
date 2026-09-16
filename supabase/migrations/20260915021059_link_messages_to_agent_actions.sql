alter table public.messages
add column action_id uuid references public.agent_actions(id) on delete set null;

create index messages_action_id_idx on public.messages(action_id);
