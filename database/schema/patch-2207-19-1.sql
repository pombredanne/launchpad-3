SET client_min_messages=ERROR;

CREATE INDEX bugtask__bugwatch__idx
ON BugTask(bugwatch) WHERE bugwatch IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 19, 1);
