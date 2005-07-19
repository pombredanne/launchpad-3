SET client_min_messages = ERROR;

-- nuke the POFile title, we will use a generated one

ALTER TABLE POFile DROP COLUMN title;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 22, 0);

