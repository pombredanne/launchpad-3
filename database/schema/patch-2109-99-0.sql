SET client_min_messages = ERROR;

ALTER TABLE Archive
    ADD COLUMN relative_build_score INTEGER;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);

