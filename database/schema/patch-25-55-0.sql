
set client_min_messages=ERROR;

ALTER TABLE BugTask ADD COLUMN targetnamecache text;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,55,0);
