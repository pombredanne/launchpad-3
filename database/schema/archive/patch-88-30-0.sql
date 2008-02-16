SET client_min_messages=ERROR;

-- Use 'IS TRUE' on indexes, to make Postgres actually match queries we
-- issue against them (previous indexes were simply 'WHERE is_current'
-- instead of 'WHERE is_current IS TRUE').
DROP INDEX translationmessage__potmsgset__pofile__is_current__key;
CREATE UNIQUE INDEX translationmessage__potmsgset__pofile__is_current__key
    ON TranslationMessage(potmsgset, pofile) WHERE is_current IS TRUE;
DROP INDEX translationmessage__potmsgset__pofile__is_imported__key;
CREATE UNIQUE INDEX translationmessage__potmsgset__pofile__is_imported__key
    ON TranslationMessage(potmsgset, pofile) WHERE is_imported IS TRUE;

-- Index all unused (neither is_imported nor is_current) suggestions as well.
CREATE INDEX translationmessage__potmsgset__pofile__not_used__key
    ON TranslationMessage(potmsgset, pofile)
    WHERE NOT (is_current IS TRUE AND is_imported IS TRUE);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 30, 0);
