SET client_min_messages=ERROR;

ALTER TABLE Product ALTER COLUMN autoupdate SET NOT NULL;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=18, patch=0;

