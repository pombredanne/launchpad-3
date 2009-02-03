SET client_min_messages=ERROR;

ALTER TABLE BugTracker
ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT true;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
