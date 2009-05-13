SET client_min_messages=ERROR;

CREATE VIEW AllLocks AS
SELECT
    a.procpid,
    a.usename,
    now() - a.query_start AS age,
    c.relname,
    l.mode,
    l.granted,
    a.current_query
FROM pg_locks l
JOIN pg_class c ON l.relation = c.oid
LEFT JOIN pg_stat_activity a ON a.procpid = l.pid;

CREATE VIEW ExclusiveLocks AS
SELECT * FROM AllLocks WHERE mode !~~ '%Share%'::text;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 33, 2);
