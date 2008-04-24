SET client_min_messages=ERROR;

CREATE TABLE BugTrackerPerson
(
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    bugtracker integer NOT NULL REFERENCES BugTracker(id),
    name text NOT NULL,
    person integer NOT NULL REFERENCES Person(id),
    CONSTRAINT bugtrackerperson__bugtracker__name__key
        UNIQUE (bugtracker, name)
);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
