SET client_min_messages TO error;

ALTER TABLE ProductBugAssignment ADD COLUMN datecreated timestamp without time zone;

ALTER TABLE ProductBugAssignment ALTER COLUMN datecreated
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';

UPDATE ProductBugAssignment SET datecreated=DEFAULT WHERE datecreated IS NULL;

ALTER TABLE ProductBugAssignment ALTER COLUMN datecreated
    SET NOT NULL;


ALTER TABLE SourcePackageBugAssignment ADD COLUMN datecreated timestamp without time zone;

ALTER TABLE SourcePackageBugAssignment ALTER COLUMN datecreated
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';

UPDATE SourcePackageBugAssignment SET datecreated=DEFAULT WHERE datecreated IS NULL;

ALTER TABLE SourcePackageBugAssignment ALTER COLUMN datecreated
    SET NOT NULL;


UPDATE LaunchpadDatabaseRevision SET major=4, minor=6, patch=0;

