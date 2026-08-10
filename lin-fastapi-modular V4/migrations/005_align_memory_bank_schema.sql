-- Align production memory_bank with the current memory conflict and review logic.
-- Safe to run repeatedly in Supabase SQL Editor.

ALTER TABLE public.memory_bank
  ADD COLUMN IF NOT EXISTS raw_keyword TEXT,
  ADD COLUMN IF NOT EXISTS pending_review BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS conflict_with BIGINT;

CREATE INDEX IF NOT EXISTS idx_memory_bank_keyword
  ON public.memory_bank (keyword);

CREATE INDEX IF NOT EXISTS idx_memory_bank_pending_review
  ON public.memory_bank (pending_review)
  WHERE pending_review = TRUE;

CREATE INDEX IF NOT EXISTS idx_memory_bank_conflict_with
  ON public.memory_bank (conflict_with)
  WHERE conflict_with IS NOT NULL;
