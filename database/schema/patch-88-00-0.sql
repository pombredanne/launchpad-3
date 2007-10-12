SET client_min_messages=ERROR;

CREATE INDEX bugtask__status__idx ON BugTask(status);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 0, 0);
