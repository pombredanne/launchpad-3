SET client_min_messages=ERROR;

ALTER TABLE Country ALTER COLUMN continent SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 09, 0);
