SET client_min_messages=ERROR;

ALTER TABLE Revision
    ADD COLUMN karma_allocated boolean DEFAULT FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
