SET client_min_messages=ERROR;

-- Fixes data problems allowed by bad unique constraints.

UPDATE TranslationMessage AS bad
SET is_current = FALSE
FROM TranslationMessage good
WHERE
    bad.id <> good.id AND
    good.potemplate = bad.potemplate AND
    good.potmsgset = bad.potmsgset AND
    bad.is_current IS TRUE AND
    good.is_current IS TRUE AND
    good.language = bad.language AND
    bad.variant IS NULL AND
    good.variant IS NULL AND
    COALESCE(good.date_reviewed, good.date_created) >
        COALESCE(bad.date_reviewed, bad.date_created);

UPDATE TranslationMessage AS bad
SET is_imported = FALSE
FROM TranslationMessage good
WHERE
    bad.id <> good.id AND
    good.potemplate = bad.potemplate AND
    good.potmsgset = bad.potmsgset AND
    bad.is_imported IS TRUE AND
    good.is_imported IS TRUE AND
    good.language = bad.language AND
    bad.variant IS NULL AND
    good.variant IS NULL AND
    COALESCE(good.date_reviewed, good.date_created) >
        COALESCE(bad.date_reviewed, bad.date_created);


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

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
