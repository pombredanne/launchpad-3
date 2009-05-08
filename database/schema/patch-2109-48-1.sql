SET client_min_messages=ERROR;

-- Fixes unique indexes from patch-44-2.sql.

DROP INDEX tm__potmsgset__potemplate__language__no_variant__diverged__current__key;
CREATE UNIQUE INDEX
    tm__potmsgset__potemplate__language__no_variant__diverged__current__key
ON translationmessage (potmsgset, potemplate, language)
WHERE ((is_current IS TRUE) AND (potemplate IS NOT NULL) AND (variant IS NULL));

DROP INDEX tm__potmsgset__potemplate__language__no_variant__diverged__imported__key;
CREATE UNIQUE INDEX
    tm__potmsgset__potemplate__language__no_variant__diverged__imported__key
ON translationmessage (potmsgset, potemplate, language)
WHERE ((is_imported IS TRUE) AND (potemplate IS NOT NULL)
    AND (variant IS NULL));

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 48, 1);
