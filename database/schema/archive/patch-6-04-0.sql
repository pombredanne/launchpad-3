SET client_min_messages=ERROR;

/* Translatable flag on Languages for Carlos */
ALTER TABLE Language ADD translatable BOOLEAN;
ALTER TABLE Language ALTER COLUMN translatable SET DEFAULT TRUE;
UPDATE Language set translatable=TRUE;
ALTER TABLE Language ALTER COLUMN translatable SET NOT NULL;


/* POTemplate/POFile constraint fixes for Carlos */
ALTER TABLE POTemplate DROP CONSTRAINT potemplate_rawimportstatus_valid;
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 1)) OR (rawfile IS NOT NULL));
ALTER TABLE POTemplate ALTER rawimportstatus SET DEFAULT 0;
UPDATE POTemplate SET rawimportstatus=0 WHERE rawimportstatus IS NULL;
ALTER TABLE POTemplate ALTER rawimportstatus SET NOT NULL;

ALTER TABLE POFile DROP CONSTRAINT pofile_rawimportstatus_valid;
ALTER TABLE POFile ADD CONSTRAINT pofile_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 1)) OR (rawfile IS NOT NULL));
ALTER TABLE POFile ALTER rawimportstatus SET DEFAULT 0;
UPDATE POFile SET rawimportstatus=0 WHERE rawimportstatus IS NULL;
ALTER TABLE POFile ALTER rawimportstatus SET NOT NULL;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=4, patch=0;
