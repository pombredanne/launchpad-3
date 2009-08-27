SET client_min_messages = ERROR;

ALTER TABLE Archive
    ADD COLUMN relative_build_score INTEGER DEFAULT 0 NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 59, 0);

