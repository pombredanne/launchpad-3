set client_min_messages = ERROR;

ALTER TABLE Bug ADD COLUMN private BOOLEAN;

UPDATE Bug SET private = FALSE;

ALTER TABLE Bug ALTER COLUMN private SET NOT NULL;
ALTER TABLE Bug ALTER COLUMN private SET DEFAULT FALSE;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=28, patch=0;
