-- Verify the schema has been created correctly.
-- Single result set; all results wrangled into a single table.

-- Verify the vector extension is installed.
select 'extension' as check, extname as name, extversion as detail
  from pg_extension
  where extname = 'vector'

union all

-- Verify the tables are created.
select 'table', table_name, null
  from information_schema.tables
  where table_schema = 'public'
    and table_name in ('documents', 'chunks')

union all

-- Verify the indexes are created.
select 'index', indexname, null
  from pg_indexes
  where tablename = 'chunks'

union all

-- Verify language code enum type is created.
select 'type', typname, null
  from pg_type
  where typname = 'lang_code'

union all

-- Verify the "updated_at" updater trigger is created.
select 'trigger', tgname, null
  from pg_trigger
  where tgname = 'documents_updated_at_trg'

union all

-- Verify the tables have row security enabled.
select 'security', tablename, rowsecurity::text
  from pg_tables
  where schemaname = 'public'
    and tablename in ('documents', 'chunks');