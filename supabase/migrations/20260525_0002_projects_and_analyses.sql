-- PROJ-21 (Analyses-Persistierung) + PROJ-22 (Multi-Projekt-Workspaces)
--
-- Single coupled migration so analyses.project_id never goes through a
-- NULL phase. Nine ordered steps:
--
--   1. analyses table (PROJ-21 core)
--   2. projects table (PROJ-22)
--   3. project_members junction (PROJ-22)
--   4. project_invites table (PROJ-22)
--   5. analyses.project_id column (nullable for migration step 6)
--   6. backfill: default project per existing user, point analyses at it
--   7. analyses.project_id -> NOT NULL
--   8. profiles.active_project_id column
--   9. extended on_auth_user_created trigger + pg_cron jobs + RLS

-- ---------------------------------------------------------------------
-- Step 1: analyses (PROJ-21)
-- ---------------------------------------------------------------------

create table if not exists public.analyses (
    id                    uuid primary key default gen_random_uuid(),
    user_id               uuid not null references auth.users(id) on delete cascade,
    source_type           text not null check (source_type in ('text', 'url', 'pdf')),
    source_reference      text,
    input_text            text not null,
    detected_claims       jsonb not null default '[]'::jsonb,
    evaluated_claims      jsonb not null default '[]'::jsonb,
    warnings              jsonb not null default '[]'::jsonb,
    prompt_version        text not null,
    model                 text not null,
    input_tokens          integer not null default 0,
    output_tokens         integer not null default 0,
    estimated_cost_usd    numeric(10, 6) not null default 0,
    latency_ms            integer not null default 0,
    created_at            timestamptz not null default now(),
    deleted_at            timestamptz
);

-- Hot-path index for the History list (replaced in step 5/9 with a
-- project_id-scoped variant once that column exists).
create index if not exists idx_analyses_user_created
    on public.analyses (user_id, created_at desc)
    where deleted_at is null;

create index if not exists idx_analyses_deleted_at
    on public.analyses (deleted_at)
    where deleted_at is not null;

-- ---------------------------------------------------------------------
-- Step 2: projects (PROJ-22)
-- ---------------------------------------------------------------------

create table if not exists public.projects (
    id          uuid primary key default gen_random_uuid(),
    name        text not null check (char_length(name) between 3 and 60),
    color       text not null default 'indigo'
                check (color in ('indigo','emerald','rose','amber','sky','violet','teal','slate')),
    is_default  boolean not null default false,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create trigger set_projects_updated_at
    before update on public.projects
    for each row
    execute function public.touch_updated_at();

-- ---------------------------------------------------------------------
-- Step 3: project_members (junction projects <-> auth.users)
-- ---------------------------------------------------------------------

create table if not exists public.project_members (
    project_id  uuid not null references public.projects(id) on delete cascade,
    user_id     uuid not null references auth.users(id) on delete cascade,
    role        text not null check (role in ('owner', 'editor', 'viewer')),
    joined_at   timestamptz not null default now(),
    primary key (project_id, user_id)
);

create index if not exists idx_project_members_user
    on public.project_members (user_id);

create index if not exists idx_project_members_project
    on public.project_members (project_id);

-- Each user can have at most one "is_default" project. Enforced via a
-- partial unique index on a derived (user_id, is_default=true) tuple
-- through a unique constraint on project_members + projects: we mark
-- exactly one owner-membership of an is_default project per user.
-- Simpler: a unique partial index on (project_members.user_id) where
-- the linked project has is_default=true. Postgres doesn't allow
-- multi-table partial indexes, so we enforce it in app code.

-- ---------------------------------------------------------------------
-- Step 4: project_invites
-- ---------------------------------------------------------------------

create table if not exists public.project_invites (
    id            uuid primary key default gen_random_uuid(),
    token         uuid not null default gen_random_uuid(),
    project_id    uuid not null references public.projects(id) on delete cascade,
    email         text not null check (email = lower(email)),
    role          text not null check (role in ('editor', 'viewer')),
    status        text not null default 'pending'
                  check (status in ('pending', 'accepted', 'revoked', 'expired')),
    invited_by    uuid not null references auth.users(id) on delete set null,
    invited_at    timestamptz not null default now(),
    expires_at    timestamptz not null default (now() + interval '7 days'),
    accepted_at   timestamptz
);

create unique index if not exists idx_project_invites_token
    on public.project_invites (token);

create index if not exists idx_project_invites_email_status
    on public.project_invites (email, status);

create index if not exists idx_project_invites_project
    on public.project_invites (project_id);

-- Prevent two pending invites to the same email for the same project.
create unique index if not exists uq_project_invites_pending
    on public.project_invites (project_id, email)
    where status = 'pending';

-- ---------------------------------------------------------------------
-- Step 5: analyses.project_id (nullable)
-- ---------------------------------------------------------------------

alter table public.analyses
    add column if not exists project_id uuid references public.projects(id) on delete cascade;

-- ---------------------------------------------------------------------
-- Step 6: backfill default projects for any existing rows
--
-- Greenfield in this deploy, but the block is idempotent so re-runs
-- against a non-empty DB are safe.
-- ---------------------------------------------------------------------

do $$
declare
    u record;
    default_project_id uuid;
begin
    for u in
        select distinct user_id
          from public.analyses
         where project_id is null
    loop
        -- Look for an existing default project the user might already own.
        select p.id
          into default_project_id
          from public.projects p
          join public.project_members m on m.project_id = p.id
         where m.user_id = u.user_id
           and p.is_default = true
         limit 1;

        if default_project_id is null then
            insert into public.projects (name, color, is_default)
            values ('Mein Workspace', 'indigo', true)
            returning id into default_project_id;

            insert into public.project_members (project_id, user_id, role)
            values (default_project_id, u.user_id, 'owner')
            on conflict do nothing;
        end if;

        update public.analyses
           set project_id = default_project_id
         where user_id = u.user_id
           and project_id is null;
    end loop;
end
$$;

-- ---------------------------------------------------------------------
-- Step 7: analyses.project_id -> NOT NULL
-- ---------------------------------------------------------------------

alter table public.analyses
    alter column project_id set not null;

-- Drop the user-only index in favour of a project-scoped one (history
-- list filters primarily by project).
drop index if exists idx_analyses_user_created;
create index if not exists idx_analyses_project_created
    on public.analyses (project_id, created_at desc)
    where deleted_at is null;

-- ---------------------------------------------------------------------
-- Step 8: profiles.active_project_id
-- ---------------------------------------------------------------------

alter table public.profiles
    add column if not exists active_project_id uuid
        references public.projects(id) on delete set null;

-- ---------------------------------------------------------------------
-- Step 9a: extend on_auth_user_created trigger
-- ---------------------------------------------------------------------

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
declare
    new_project_id uuid;
begin
    -- 1. Profile (was the original PROJ-1 behaviour).
    insert into public.profiles (id)
    values (new.id)
    on conflict (id) do nothing;

    -- 2. Default project + owner membership.
    insert into public.projects (name, color, is_default)
    values ('Mein Workspace', 'indigo', true)
    returning id into new_project_id;

    insert into public.project_members (project_id, user_id, role)
    values (new_project_id, new.id, 'owner');

    -- 3. Point profile at the default project.
    update public.profiles
       set active_project_id = new_project_id
     where id = new.id;

    return new;
end;
$$;

-- ---------------------------------------------------------------------
-- Step 9b: pg_cron jobs (soft-delete purge + invite cleanup)
-- ---------------------------------------------------------------------

create extension if not exists pg_cron;

-- Daily purge of soft-deleted analyses older than 30 days.
select cron.schedule(
    'purge_soft_deleted_analyses',
    '15 3 * * *',
    $$ delete from public.analyses
        where deleted_at is not null
          and deleted_at < now() - interval '30 days' $$
);

-- Daily invite cleanup: expire pending > 7 days, delete non-pending > 30 days.
select cron.schedule(
    'cleanup_project_invites',
    '20 3 * * *',
    $$
    update public.project_invites
       set status = 'expired'
     where status = 'pending'
       and expires_at < now();
    delete from public.project_invites
     where status <> 'pending'
       and invited_at < now() - interval '30 days';
    $$
);

-- ---------------------------------------------------------------------
-- Step 9c: Row-Level Security
-- ---------------------------------------------------------------------

alter table public.analyses enable row level security;
alter table public.projects enable row level security;
alter table public.project_members enable row level security;
alter table public.project_invites enable row level security;

-- ----- projects -------------------------------------------------------
create policy "projects_select_member"
    on public.projects
    for select
    using (
        exists (
            select 1
              from public.project_members m
             where m.project_id = projects.id
               and m.user_id = auth.uid()
        )
    );

create policy "projects_insert_authenticated"
    on public.projects
    for insert
    with check (auth.uid() is not null);

create policy "projects_update_owner"
    on public.projects
    for update
    using (
        exists (
            select 1
              from public.project_members m
             where m.project_id = projects.id
               and m.user_id = auth.uid()
               and m.role = 'owner'
        )
    )
    with check (
        exists (
            select 1
              from public.project_members m
             where m.project_id = projects.id
               and m.user_id = auth.uid()
               and m.role = 'owner'
        )
    );

create policy "projects_delete_owner"
    on public.projects
    for delete
    using (
        exists (
            select 1
              from public.project_members m
             where m.project_id = projects.id
               and m.user_id = auth.uid()
               and m.role = 'owner'
        )
    );

-- ----- project_members -----------------------------------------------
create policy "members_select_co_member"
    on public.project_members
    for select
    using (
        exists (
            select 1
              from public.project_members m
             where m.project_id = project_members.project_id
               and m.user_id = auth.uid()
        )
    );

create policy "members_insert_owner"
    on public.project_members
    for insert
    with check (
        exists (
            select 1
              from public.project_members m
             where m.project_id = project_members.project_id
               and m.user_id = auth.uid()
               and m.role = 'owner'
        )
    );

create policy "members_update_owner"
    on public.project_members
    for update
    using (
        exists (
            select 1
              from public.project_members m
             where m.project_id = project_members.project_id
               and m.user_id = auth.uid()
               and m.role = 'owner'
        )
    );

create policy "members_delete_owner_or_self"
    on public.project_members
    for delete
    using (
        user_id = auth.uid()
        or exists (
            select 1
              from public.project_members m
             where m.project_id = project_members.project_id
               and m.user_id = auth.uid()
               and m.role = 'owner'
        )
    );

-- ----- project_invites -----------------------------------------------
create policy "invites_select_owner"
    on public.project_invites
    for select
    using (
        exists (
            select 1
              from public.project_members m
             where m.project_id = project_invites.project_id
               and m.user_id = auth.uid()
               and m.role = 'owner'
        )
    );

create policy "invites_insert_owner"
    on public.project_invites
    for insert
    with check (
        exists (
            select 1
              from public.project_members m
             where m.project_id = project_invites.project_id
               and m.user_id = auth.uid()
               and m.role = 'owner'
        )
    );

create policy "invites_update_owner"
    on public.project_invites
    for update
    using (
        exists (
            select 1
              from public.project_members m
             where m.project_id = project_invites.project_id
               and m.user_id = auth.uid()
               and m.role = 'owner'
        )
    );

-- ----- analyses -------------------------------------------------------
create policy "analyses_select_member"
    on public.analyses
    for select
    using (
        deleted_at is null
        and exists (
            select 1
              from public.project_members m
             where m.project_id = analyses.project_id
               and m.user_id = auth.uid()
        )
    );

create policy "analyses_insert_member_with_write"
    on public.analyses
    for insert
    with check (
        user_id = auth.uid()
        and exists (
            select 1
              from public.project_members m
             where m.project_id = analyses.project_id
               and m.user_id = auth.uid()
               and m.role in ('owner', 'editor')
        )
    );

create policy "analyses_update_member_with_write"
    on public.analyses
    for update
    using (
        exists (
            select 1
              from public.project_members m
             where m.project_id = analyses.project_id
               and m.user_id = auth.uid()
               and m.role in ('owner', 'editor')
        )
    );

create policy "analyses_delete_member_with_write"
    on public.analyses
    for delete
    using (
        exists (
            select 1
              from public.project_members m
             where m.project_id = analyses.project_id
               and m.user_id = auth.uid()
               and m.role in ('owner', 'editor')
        )
    );
