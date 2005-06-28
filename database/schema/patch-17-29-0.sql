
SET client_min_messages=ERROR;

ALTER TABLE Product ADD COLUMN releaseroot text;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 29, 0);
