-- Phase 8: shared attachment metadata for Chat and future Agent surfaces.
-- Object bytes live in the private attachments Storage bucket; metadata is soft-deleted.

create table if not exists public.attachments (
  id uuid primary key default gen_random_uuid(),
  attachment_id text not null unique,
  owner_type text not null check (owner_type in ('chat', 'agent')),
  owner_id text,
  kind text not null check (kind in ('image', 'file')),
  filename text not null,
  object_key text not null unique,
  mime_type text not null,
  size_bytes bigint not null check (size_bytes > 0),
  sha256 text not null,
  status text not null default 'uploaded' check (status in ('uploaded', 'deleted')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index if not exists idx_attachments_owner_created
  on public.attachments (owner_type, owner_id, created_at desc);

create index if not exists idx_attachments_status_created
  on public.attachments (status, created_at desc);

alter table public.attachments enable row level security;

-- Create a private Storage bucket named `attachments` in Storage → New bucket.
-- Do not make it public: the application uses service_role credentials to issue URLs.
