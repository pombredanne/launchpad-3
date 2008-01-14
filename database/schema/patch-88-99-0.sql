SET client_min_messages=ERROR;

ALTER TABLE Archive
    ADD COLUMN private boolean;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
