set client_min_messages=ERROR;

ALTER TABLE BugTask ALTER COLUMN priority DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 35, 0);

