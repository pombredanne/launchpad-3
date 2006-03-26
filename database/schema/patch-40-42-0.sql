SET client_min_messages=ERROR;

ALTER TABLE Branch ADD COLUMN mirror_status_message text;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 42, 0);
