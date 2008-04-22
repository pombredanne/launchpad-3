SET client_min_messages=ERROR;


ALTER TABLE BugMessage ADD COLUMN hidden BOOLEAN
    NOT NULL DEFAULT FALSE;


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
