-- Phase 7: candidate lifecycle, action outbox, and audit.
-- Independent migration. Phase 6 tables remain unchanged.
create table if not exists public.life_candidates (
  id uuid primary key default gen_random_uuid(),
  candidate_id text not null unique,
  source_event_id text not null,
  route text not null,
  category text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  priority double precision not null default 0,
  score double precision not null default 0,
  status text not null default 'pending',
  context_snapshot jsonb not null default '{}'::jsonb,
  decision text,
  decision_reason text,
  action_reference text,
  updated_at timestamptz not null default now()
);
create unique index if not exists idx_life_candidates_source_route on public.life_candidates (source_event_id, route);
create index if not exists idx_life_candidates_status_created on public.life_candidates (status, created_at desc);
create index if not exists idx_life_candidates_expires on public.life_candidates (expires_at);

create table if not exists public.life_action_outbox (
  id uuid primary key default gen_random_uuid(),
  outbox_id text not null unique,
  candidate_id text not null,
  action text not null,
  idempotency_key text not null unique,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'pending',
  attempts integer not null default 0,
  next_attempt_at timestamptz,
  last_error text,
  result jsonb,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_life_outbox_status_attempt on public.life_action_outbox (status, next_attempt_at);
create index if not exists idx_life_outbox_candidate on public.life_action_outbox (candidate_id);

create table if not exists public.life_action_audit (
  id uuid primary key default gen_random_uuid(),
  audit_id text not null unique,
  candidate_id text not null,
  stage text not null,
  status text not null,
  reason text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_life_audit_candidate_time on public.life_action_audit (candidate_id, created_at desc);
create index if not exists idx_life_audit_stage_status on public.life_action_audit (stage, status);

alter table public.life_candidates enable row level security;
alter table public.life_action_outbox enable row level security;
alter table public.life_action_audit enable row level security;
