SET client_min_messages = ERROR;

ALTER TABLE BugTask
ADD COLUMN date_left_closed TIMESTAMP WITHOUT TIME ZONE NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
