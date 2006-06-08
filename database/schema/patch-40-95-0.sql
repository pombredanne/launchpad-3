SET client_min_messages=ERROR;

ALTER TABLE Branch ADD COLUMN last_scanned TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE Branch ADD COLUMN last_scanned_id STRING;
ALTER TABLE Branch ADD COLUMN last_mirrored_id STRING;


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 95, 0);
