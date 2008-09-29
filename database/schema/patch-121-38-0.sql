SET client_min_messages=ERROR;


ALTER TABLE BugMessage ADD COLUMN visible BOOLEAN
    NOT NULL DEFAULT TRUE;


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 38, 0);
