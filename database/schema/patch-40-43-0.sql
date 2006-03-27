SET client_min_messages=ERROR;

CREATE TABLE BugNotification (
    id SERIAL PRIMARY KEY,
    bug INT NOT NULL REFERENCES Bug(id),
    message INT NOT NULL REFERENCES Message(id),
    is_comment BOOL NOT NULL,
    date_emailed TIMESTAMP,
    CONSTRAINT bugnotification__bug__message__unq UNIQUE (bug, message)
    );

CREATE INDEX bugnotification__date_emailed__idx
    ON BugNotification(date_emailed);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 43, 0);
