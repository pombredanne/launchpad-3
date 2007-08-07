SET client_min_messages=ERROR;

ALTER TABLE BugMessage
ADD COLUMN bugwatch INTEGER DEFAULT NULL REFERENCES BugWatch;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);

