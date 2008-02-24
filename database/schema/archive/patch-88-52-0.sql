SET client_min_messages=ERROR;

ALTER TABLE Archive ADD COLUMN private boolean NOT NULL DEFAULT FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 52, 0);
