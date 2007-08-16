SET client_min_messages=ERROR;

ALTER TABLE BugMessage
ADD COLUMN bugwatch INTEGER DEFAULT NULL REFERENCES BugWatch;

CREATE INDEX bugmessage__bugwatch__idx ON BugMessage(bugwatch);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 40, 0);

