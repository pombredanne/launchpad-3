SET client_min_messages=ERROR;

ALTER TABLE BugTracker ADD COLUMN version TEXT;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 27, 0);
