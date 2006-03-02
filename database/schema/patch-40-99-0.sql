SET client_min_messages=ERROR;

/* Allow status and severity to be NULL, so that we can use it to
 * indicate that the column hasn't been updated by a bug watch. /*
ALTER TABLE BugTask ALTER COLUMN status DROP NOT NULL;
ALTER TABLE BugTask ALTER COLUMN severity DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);

