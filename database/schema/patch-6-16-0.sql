SET client_min_messages=ERROR;

ALTER TABLE POTranslationSighting ALTER COLUMN LICENSE DROP NOT NULL;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=16, patch=0;

