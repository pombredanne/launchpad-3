SET client_min_messages = error;
-- Fixes unique indexes from patch-44-2.sql: replace two partial unique
-- indexes that include the variant column but are for cases where variant
-- is null.  The replacements leave out variant.
-- Creating the new index before dropping the old one, in case it's of any
-- use while creating the new one.

ALTER INDEX
    tm__potmsgset__potemplate__language__no_variant__diverged__current__key
RENAME TO tm__old__diverged__current__key;
CREATE UNIQUE INDEX
    tm__potmsgset__potemplate__language__no_variant__diverged__current__key
ON translationmessage (potmsgset, potemplate, language)
WHERE is_current IS TRUE AND potemplate IS NOT NULL AND variant IS NULL;
DROP INDEX tm__old__diverged__current__key;

ALTER INDEX
    tm__potmsgset__potemplate__language__no_variant__diverged__imported__key
RENAME TO tm__old__diverged__imported__key;
CREATE UNIQUE INDEX
    tm__potmsgset__potemplate__language__no_variant__diverged__imported__key
ON TranslationMessage(potmsgset, potemplate, language)
WHERE is_imported IS TRUE AND potemplate IS NOT NULL AND variant IS NULL;
DROP INDEX tm__old__diverged__imported__key;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 51, 2);
