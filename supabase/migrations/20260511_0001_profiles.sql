-- PROJ-1: User Authentication
--
-- Public profiles table that hangs 1:1 off Supabase's auth.users.
-- A SECURITY DEFINER trigger fires on every new auth.users row and
-- inserts a matching profiles row in the same transaction, so we can
-- never end up with users that have no profile.
--
-- RLS: each user only sees/edits their own row. The backend uses the
-- service role key for inserts/lookups, and validates auth.uid()
-- against the requesting user's JWT as a defense-in-depth check.

create table if not exists public.profiles (
    id                    uuid primary key references auth.users(id) on delete cascade,
    display_name          text,
    avatar_url            text,
    onboarding_completed  boolean not null default false,
    created_at            timestamptz not null default now(),
    updated_at            timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "profiles_select_own"
    on public.profiles
    for select
    using (auth.uid() = id);

create policy "profiles_update_own"
    on public.profiles
    for update
    using (auth.uid() = id)
    with check (auth.uid() = id);

-- Inserts and deletes are not exposed to clients; the trigger handles
-- inserts on signup, and ON DELETE CASCADE from auth.users handles
-- account deletion. No policies needed for INSERT/DELETE - they fall
-- through to the default deny.

-- Auto-populate profile when a new auth.users row appears.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
begin
    insert into public.profiles (id)
    values (new.id)
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row
    execute function public.handle_new_user();

-- Keep updated_at fresh on every UPDATE.
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists set_profiles_updated_at on public.profiles;
create trigger set_profiles_updated_at
    before update on public.profiles
    for each row
    execute function public.touch_updated_at();
