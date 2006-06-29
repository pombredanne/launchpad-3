SET client_min_messages=ERROR;

ALTER TABLE Branch ADD COLUMN last_scanned timestamp without time zone;
ALTER TABLE Branch ADD COLUMN last_scanned_id text;
ALTER TABLE Branch ADD COLUMN last_mirrored_id text;


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 66, 0);
