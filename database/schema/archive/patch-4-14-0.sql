

/*
  remove NOT NULL requirement on fields that are not set until the
  bug watch status has been checked at least once.
*/

ALTER TABLE BugWatch ALTER COLUMN remotestatus DROP NOT NULL;
ALTER TABLE BugWatch ALTER COLUMN lastchanged DROP NOT NULL;
ALTER TABLE BugWatch ALTER COLUMN lastchecked DROP NOT NULL;

UPDATE LaunchpadDatabaseRevision SET major=4, minor=14, patch=0;

