SET client_min_messages=ERROR;

ALTER TABLE BugTracker ALTER COLUMN title DROP NOT NULL;
ALTER TABLE BugTracker ALTER COLUMN summary DROP NOT NULL;
ALTER TABLE BugTracker ALTER COLUMN contactdetails DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (99, 0, 0);