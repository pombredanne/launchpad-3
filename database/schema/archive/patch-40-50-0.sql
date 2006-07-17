SET client_min_messages=error;

ALTER TABLE BugTask ADD COLUMN date_confirmed timestamp without time zone;
ALTER TABLE BugTask ADD COLUMN date_inprogress timestamp without time zone;
ALTER TABLE BugTask ADD COLUMN date_closed timestamp without time zone;
ALTER TABLE BugTask RENAME COLUMN dateassigned TO date_assigned;
ALTER TABLE BugTask ALTER COLUMN date_assigned SET DEFAULT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 50, 0);