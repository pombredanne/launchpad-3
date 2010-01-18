SET client_min_messages=ERROR;

CREATE TABLE BugHeatJob(
    id integer NOT NULL PRIMARY KEY,
    job integer NOT NULL REFERENCES Job(id),
    bug integer NOT NULL REFERENCES Bug(id)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0)
