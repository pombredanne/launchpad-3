SET client_min_messages = ERROR;

-- NOTE: This is not the original patch 2209-00-5. That was originally
-- to support 8.4 and 9.1, but it failed to apply in 9.3, so history was
-- altered to make it support 9.1 and 9.3 instead. It's duplicated as
-- 2209-53-1 to ensure the new version is applied to systems that
-- already have 2209-00-5.

-- Compatibility code. During transition, we need code that runs with
-- both PostgreSQL 9.1 and 9.3. Once we're on 9.3 this can probably be
-- replaced with a simple SQL function.

CREATE OR REPLACE FUNCTION activity()
RETURNS SETOF pg_stat_activity
VOLATILE SECURITY DEFINER SET search_path = public
LANGUAGE plpgsql AS $$
DECLARE
    a pg_stat_activity%ROWTYPE;
BEGIN
    IF EXISTS (
            SELECT 1 FROM pg_attribute WHERE
                attrelid =
                    (SELECT oid FROM pg_class
                     WHERE relname = 'pg_stat_activity')
                AND attname = 'procpid') THEN
        RETURN QUERY SELECT
            datid, datname, procpid, usesysid, usename, application_name,
            client_addr, client_hostname, client_port, backend_start,
            xact_start, query_start, waiting,
            CASE
                WHEN current_query LIKE '<IDLE>%'
                    OR current_query LIKE 'autovacuum:%'
                    THEN current_query
                ELSE
                    '<HIDDEN>'
            END AS current_query
        FROM pg_catalog.pg_stat_activity;
    ELSE
        RETURN QUERY SELECT
            datid, datname, pid, usesysid, usename, application_name,
            client_addr, client_hostname, client_port, backend_start,
            xact_start, query_start, state_change, waiting, state,
            CASE
                WHEN query LIKE '<IDLE>%'
                    OR query LIKE 'autovacuum:%'
                    THEN query
                ELSE
                    '<HIDDEN>'
            END AS query
        FROM pg_catalog.pg_stat_activity;
    END IF;
END;
$$;


INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 0, 5);
