SET client_min_messages TO ERROR;

ALTER TABLE POTranslation DROP CONSTRAINT potranslation_translation_key;
CREATE UNIQUE INDEX potranslation_translation_key
    ON POTranslation (sha1(translation));

UPDATE LaunchpadDatabaseRevision SET major=6, minor=26, patch=0;

