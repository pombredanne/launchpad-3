set client_min_messages = ERROR;

ALTER TABLE POTemplate ADD header text;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=30, patch=0;
