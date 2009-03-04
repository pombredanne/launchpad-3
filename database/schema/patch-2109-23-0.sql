SET client_min_messages=ERROR;

ALTER TABLE BugTracker
ADD COLUMN active BOOLEAN NOT NULL DEFAULT true;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 23, 0);
