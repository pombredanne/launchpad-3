SET client_min_messages=ERROR;

CREATE TABLE BugTag (
    id SERIAL PRIMARY KEY,
    bug INTEGER NOT NULL,
    tag TEXT NOT NULL);


INSERT INTO LaunchpadDatabaseRevision VALUES (67, 99, 0);
