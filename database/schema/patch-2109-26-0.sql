SET client_min_messages=ERROR;

UPDATE Branch
SET lifecycle_status=30 -- DEVELOPMENT
WHERE lifecycle_status=1; -- NEW

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 26, 0);
