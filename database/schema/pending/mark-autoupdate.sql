ALTER TABLE Product ALTER COLUMN autoupdate SET NOT NULL;

UPDATE LaunchpadDatabaseRevision SET major=6,minor=11,patch=0;

