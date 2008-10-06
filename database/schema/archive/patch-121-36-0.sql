SET client_min_messages=ERROR;

ALTER TABLE BugTask
  ADD COLUMN date_left_new timestamp without time zone,
  ADD COLUMN date_triaged timestamp without time zone,
  ADD COLUMN date_fix_committed timestamp without time zone,
  ADD COLUMN date_fix_released timestamp without time zone;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 36, 0);
