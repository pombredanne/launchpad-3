SET client_min_messages=ERROR;

ALTER TABLE BugWatch ADD COLUMN remote_importance text;
INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
