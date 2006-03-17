SET client_min_messages=ERROR;

CREATE TABLE BugNotification (
    id SERIAL PRIMARY KEY,
    bug INT NOT NULL REFERENCES Bug(id),
    message INT NOT NULL REFERENCES Message(id),
    is_comment BOOL NOT NULL,
    date_emailed TIMESTAMP
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);

