# Pulse Storage

Supabase-backed storage module for LinkedIn Pulse Reader.

The package is intentionally split into:

- `storage.core` - reusable Supabase client/settings helpers.
- `storage.domain.pulse` - product-specific repositories for current tables.
- `storage.PulseStorage` - small facade that wires the current repositories.

## Supabase Cloud Setup Via Dashboard

1. Open Supabase Dashboard.
2. Go to **Project Settings -> API** and copy:
   - `SUPABASE_URL` from Project URL.
   - `SUPABASE_SERVICE_ROLE_KEY` from `service_role` secret for worker usage.
   - `SUPABASE_ANON_KEY` from `anon public` for future user-facing RLS usage.
3. Go to **Authentication -> Users**.
   - Create or select a user.
   - Copy **User UID** as `STORAGE_USER_ID`.

Never commit `SUPABASE_SERVICE_ROLE_KEY`. If it was exposed, rotate it in Supabase before using it.

## Apply Schema In Dashboard

Run the migrations in **SQL Editor** in this order:

1. `../supabase/migrations/20260510221600_create_linkedin_accounts_and_feed_posts.sql`
2. `../supabase/migrations/20260510221610_rls_policies_for_storage.sql`

Verify tables:

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('linkedin_accounts', 'feed_posts');
```

Expected result: `linkedin_accounts` and `feed_posts`.

## Runtime Environment

For worker ingestion:

```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<secret>"
export STORAGE_USER_ID="<auth.users.id>"
export STORAGE_ACCOUNT_LABEL="default" # optional
```

For future user-facing access:

```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_ANON_KEY="<anon-key>"
```

Then pass the user's JWT to `create_supabase_client(user_jwt=...)`.

Local Supabase URLs are rejected by default. Use `SUPABASE_ALLOW_LOCAL_URL=1` only for explicit local debugging.

## Install

From the repository root:

```bash
python3 -m pip install -e Storage
```

## Basic Usage

```python
from storage import PulseStorage

storage = PulseStorage()

accounts = storage.linkedin_accounts.list_by_user(user_id="<auth-user-id>")
posts = storage.feed_posts.list_for_account(linkedin_account_id=accounts[0]["id"])
```

## Extending The Module

For a new table:

1. Add a SQL migration.
2. Add row/input types under `storage.domain.<project>.models`.
3. Add a repository with explicit methods for real use-cases.
4. Export the repository from the domain package or add it to a facade.

Avoid generic repositories, Unit of Work, and event abstractions until there is real duplication or multiple callers that need them.

