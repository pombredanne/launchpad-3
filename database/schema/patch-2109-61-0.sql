SET client_min_messages=ERROR;

ALTER TABLE BugBranch DROP status;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 61, 0);
