SET client_min_messages TO error;

/*
 * Rosetta fixes
 *
 * With the rename from deprecated to active in patch-1-1-0
 * we forgot to change the default value.
 */
ALTER TABLE POTranslationSighting ALTER COLUMN active SET DEFAULT TRUE;

/*
 * A plural form could have the same translation for some numbers
 */
ALTER TABLE POTranslationSighting
    DROP CONSTRAINT "potranslationsighting_pomsgset_key";
ALTER TABLE POTranslationSighting
    ADD CONSTRAINT "potranslationsighting_pomsgset_key"
    UNIQUE(pomsgset, potranslation, license, person, pluralform)

