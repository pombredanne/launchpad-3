SET client_min_messages=ERROR;

ALTER TABLE BugTask ALTER COLUMN status DROP NOT NULL;
ALTER TABLE BugTask ALTER COLUMN severity DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);

