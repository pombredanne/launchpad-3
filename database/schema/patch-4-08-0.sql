SET client_min_messages TO error;

/* Add owner to bug assignment tables */

ALTER TABLE SourceSource ADD COLUMN branchpoint text;

UPDATE LaunchpadDatabaseRevision SET major=4, minor=8, patch=0;

