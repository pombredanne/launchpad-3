SET client_min_messages=ERROR;

CREATE UNIQUE INDEX buildqueue__builder__unq ON BuildQueue(builder)
WHERE builder IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 35, 1);

