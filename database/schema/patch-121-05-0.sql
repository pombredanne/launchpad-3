SET client_min_messages=ERROR;

ALTER TABLE POFile DROP COLUMN exportfile;
ALTER TABLE POFile DROP COLUMN exporttime;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 05, 0);
