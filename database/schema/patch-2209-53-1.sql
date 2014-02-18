SET client_min_messages = ERROR;

-- NOTE: This is a duplicate of 2209-00-5. See 2209-00-5.sql for
-- rationale.

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


INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 53, 1);
