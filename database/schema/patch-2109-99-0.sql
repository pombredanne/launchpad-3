SET client_min_messages=ERROR;

ALTER TABLE Archive DROP COLUMN whiteboard;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);

