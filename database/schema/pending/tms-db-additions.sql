-- BEGIN; -- XXX: DEBUG

SET client_min_messages=ERROR;


-- Add columns
ALTER TABLE TranslationMessage
    ADD COLUMN potemplate integer REFERENCES POTemplate(id),
    ADD COLUMN language integer REFERENCES Language(id),
    ADD COLUMN variant text;

-- Create linking table
CREATE TABLE TranslationTemplateItem(
    id serial PRIMARY KEY,
    potemplate integer NOT NULL REFERENCES POTemplate(id),
    potmsgset integer NOT NULL REFERENCES POTMsgSet(id));

CREATE UNIQUE INDEX translationtemplateitem__potemplate__potmsgset__key
ON TranslationTemplateItem(potemplate, potmsgset);

CREATE INDEX translationtemplateitem__potmsgset__idx
ON TranslationTemplateItem(potmsgset);

-- Populate linking table
-- INSERT INTO TranslationTemplateItem(potemplate, potmsgset)
-- SELECT potemplate, id
-- FROM potmsgset;
-- 
-- 
-- Initialize new columns
-- UPDATE TranslationMessage
-- SET
--     potemplate = POTMsgSet.potemplate,
--     language = POFile.language,
--     variant = POFile.variant
-- FROM
--     POTMsgSet, POFile
-- WHERE
--     POTMsgSet.id = TranslationMessage.potmsgset AND
--     POFile.id = TranslationMessage.pofile;
-- 
-- ALTER TABLE TranslationMessage ALTER language SET NOT NULL;
-- 

-- TODO: Merge POTMsgSets
-- TODO: Merge TranslationMessages


-- Drop obsolete columns
-- ALTER TABLE TranslationMessage DROP COLUMN pofile CASCADE;
-- 
-- ALTER TABLE POTMsgSet DROP COLUMN potemplate CASCADE;
-- 
-- CREATE UNIQUE INDEX
--     translationmessage__language__potemplate__potmsgset__msgstrs__key
-- ON TranslationMessage(
--     COALESCE(potemplate, -1),
--     potmsgset,
--     language,
--     COALESCE(variant, ''),
--     COALESCE(msgstr0, -1),
--     COALESCE(msgstr1, -1),
--     COALESCE(msgstr2, -1),
--     COALESCE(msgstr3, -1),
--     COALESCE(msgstr4, -1),
--     COALESCE(msgstr5, -1));
-- 
-- CREATE UNIQUE INDEX
--     translationmessage__potmsgset__language__is_current__key
-- ON TranslationMessage(potmsgset, language, COALESCE(variant, ''))
-- WHERE is_current IS TRUE;
-- 
-- CREATE UNIQUE INDEX
--     translationmessage__potmsgset__language__is_imported__key
-- ON TranslationMessage(potmsgset, language, COALESCE(variant, ''))
-- WHERE is_imported IS TRUE;
-- 
-- CREATE INDEX translationmessage__language__submitter__idx
-- ON TranslationMessage(language, COALESCE(variant, ''), submitter);
-- 
-- CREATE INDEX translationmessage__potmsgset__language__not_used__key
-- ON TranslationMessage(potmsgset, language, COALESCE(variant, ''))
-- WHERE NOT (is_current IS TRUE AND is_imported IS TRUE);

-- INSERT INTO LaunchpadDatabaseRevision VALUES (x, y, 0);

-- TODO: Change POFileTranslator trigger functions.

-- ROLLBACK; -- XXX: DEBUG

