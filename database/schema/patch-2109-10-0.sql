SET client_min_messages = ERROR;

ALTER TABLE BugTask
ADD COLUMN date_left_closed TIMESTAMP WITHOUT TIME ZONE;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 10, 0);
