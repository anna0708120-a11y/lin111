-- Phase 6: normalized Life Events and replayable Life State snapshots.
-- Independent migration. Existing tables are untouched.
create table if not exists public.life_events (
  id uuid primary key default gen_random_uuid(),
  event_id text not null unique,
  event_type text not null,
  source text not null,
  subject_id text not null default 'anna',
  session_id text,
  occurred_at timestamptz not null,
  received_at timestamptz not null,
  payload jsonb not null default '{}'::jsonb,
  confidence double precision not null default 1.0 check (confidence >= 0 and confidence <= 1),
  dedupe_key text not null unique,
  schema_version integer not null default 1,
  created_at timestamptz not null default now()
);

create index if not exists idx_life_events_occurred_at on public.life_events (occurred_at);
create index if not exists idx_life_events_subject_time on public.life_events (subject_id, occurred_at desc);
create index if not exists idx_life_events_type_time on public.life_events (event_type, occurred_at desc);

create table if not exists public.life_state_snapshots (
  id uuid primary key default gen_random_uuid(),
  snapshot_id text not null unique,
  subject_id text not null default 'anna',
  state jsonb not null default '{}'::jsonb,
  changed_keys jsonb not null default '[]'::jsonb,
  source_event_id text,
  valid_at timestamptz not null,
  created_at timestamptz not null default now(),
  version integer not null,
  unique (subject_id, version)
);

create index if not exists idx_life_state_subject_version on public.life_state_snapshots (subject_id, version desc);
create index if not exists idx_life_state_valid_at on public.life_state_snapshots (valid_at desc);

alter table public.life_events enable row level security;
alter table public.life_state_snapshots enable row level security;
