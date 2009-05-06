SET client_min_messages=ERROR;

-- This is half of a two part patch. The first half is patch-2109-44-2.sql,
-- which is the half we will attempt to apply to production before
-- the next rollout (after changing the CREATE INDEX statements to
-- CREATE INDEX CONCURRENTLY). This half of the patch cleans up indexes
-- that should no longer be needed after the rollout.

-- Relax database constraints for message-sharing, and provide indexes
-- to ensure acceptable performance levels.

-- POTMsgSet table changes.

-- Replaced by indexes used to match global suggestions in patch-2109-44-2.sql
DROP INDEX potmsgset__potemplate__context__msgid_singular__msgid_plural__k;
DROP INDEX potmsgset__potemplate__context__msgid_singular__no_msgid_plural;
DROP INDEX potmsgset__potemplate__no_context__msgid_singular__msgid_plural;
DROP INDEX potmsgset__potemplate__no_context__msgid_singular__no_msgid_plu;


-- TranslationTemplateItem changes.

-- A POTemplate can have only one row with a certain sequence number.
DROP INDEX potmsgset_potemplate_and_sequence_idx;


-- Replace constraint with one allowing sequence of zero.
ALTER TABLE TranslationTemplateItem
  DROP CONSTRAINT translationtemplateitem_sequence_check;
ALTER TABLE TranslationTemplateItem
  ADD CONSTRAINT translationtemplateitem_sequence_check CHECK (sequence >= 0);

-- No need to set potmsgset.potemplate and sequence columns.
-- XXX Danilo: message sharing DB clean-up should drop these columns.
ALTER TABLE potmsgset
    ALTER COLUMN potemplate DROP NOT NULL,
    ALTER COLUMN sequence DROP NOT NULL;

-- TranslationMessage table changes.
-- Removes pointers to PO file and replaces them with (language, variant) pair.
-- Also provides for shared (potemplate IS NULL) and
-- diverged (potemplate IS NOT NULL) messages.

-- No need to set translationmessage.pofile column.
-- XXX Danilo: message sharing DB clean-up should drop the column.
ALTER TABLE translationmessage ALTER COLUMN pofile DROP NOT NULL;

-- These are used for doing DISTINCT over all matching global suggestions.
-- XXX Danilo: they won't be needed as much after migration.
DROP INDEX translationmessage__pofile__potmsgset__msgstrs__key;
-- XXX Stub: As per IRC discussions, these are being dropped for now.
-- we can reenable them post-rollout to ensure migration works as expected.
-- CREATE UNIQUE INDEX tm__potmsgset__language__variant__shared__msgstrs__key
-- ON translationmessage (
--     potmsgset, language, variant, potemplate,
--     (COALESCE(msgstr0, -1)), (COALESCE(msgstr1, -1)),
--     (COALESCE(msgstr2, -1)), (COALESCE(msgstr3, -1)),
--     (COALESCE(msgstr4, -1)), (COALESCE(msgstr5, -1)))
-- WHERE (potemplate IS NULL AND variant IS NOT NULL);
-- CREATE UNIQUE INDEX
--     tm__potmsgset__language__no_variant__shared__msgstrs__key
-- ON translationmessage (
--     potmsgset, language, potemplate, (COALESCE(msgstr0, -1)),
--     (COALESCE(msgstr1, -1)), (COALESCE(msgstr2, -1)),
--     (COALESCE(msgstr3, -1)), (COALESCE(msgstr4, -1)),
--     (COALESCE(msgstr5, -1)))
-- WHERE (potemplate IS NULL AND variant IS NULL);
-- CREATE UNIQUE INDEX
--     tm__potmsgset__potemplate__language__variant__diverged__msgstrs__key
-- ON translationmessage (
--     potmsgset, potemplate, language, variant, (COALESCE(msgstr0, -1)),
--     (COALESCE(msgstr1, -1)), (COALESCE(msgstr2, -1)),
--     (COALESCE(msgstr3, -1)), (COALESCE(msgstr4, -1)),
--     (COALESCE(msgstr5, -1)))
-- WHERE (potemplate IS NOT NULL AND variant IS NOT NULL);
-- CREATE UNIQUE INDEX
--     tm__potmsgset__potemplate__language__no_variant__diverged__msgstrs__key
-- ON translationmessage (
--     potmsgset, potemplate, language, (COALESCE(msgstr0, -1)),
--     (COALESCE(msgstr1, -1)), (COALESCE(msgstr2, -1)),
--     (COALESCE(msgstr3, -1)), (COALESCE(msgstr4, -1)),
--     (COALESCE(msgstr5, -1)))
-- WHERE (potemplate IS NOT NULL AND variant IS NULL);

-- A POFile link is gone from translationmessage, replaced with
-- language/variant combination, where variant can be NULL.
DROP INDEX translationmessage__pofile__submitter__idx;

-- Indexes to fetch current messages: there can be at most one shared
-- (potemplate IS NULL) and one diverged (potemplate = X) is_current message.
-- Split into 4 to cope with NULL handling for potemplate and variant fields.
DROP INDEX translationmessage__potmsgset__pofile__is_current__key;

-- Indexes to fetch imported messages: there can be at most one shared
-- (potemplate IS NULL) and one diverged (potemplate = X) is_imported message.
-- Split into 4 to cope with NULL handling for potemplate and variant fields.
DROP INDEX translationmessage__potmsgset__pofile__is_imported__key;

-- Speed up local suggestions look-up by setting up a partial index
-- for messages which are neither is_current nor is_imported.
-- This should help because relation of unused TMs compared to used
-- is around 1/10.
-- XXX Danilo: previous index was not UNIQUE even if __key suggests it was.
DROP INDEX translationmessage__potmsgset__pofile__not_used__key;


-- Replace POTExport with a view going through TranslationTemplateItem.
DROP VIEW potexport;
CREATE VIEW potexport AS
    SELECT COALESCE((potmsgset.id)::text, 'X'::text) AS id,
    potemplate.productseries,
    potemplate.sourcepackagename,
    potemplate.distroseries,
    potemplate.id AS potemplate,
    potemplate.header AS template_header,
    potemplate.languagepack,
    translationtemplateitem.sequence,
    potmsgset.id AS potmsgset,
    potmsgset.commenttext AS comment,
    potmsgset.sourcecomment AS source_comment,
    potmsgset.filereferences AS file_references,
    potmsgset.flagscomment AS flags_comment,
    potmsgset.context,
    msgid_singular.msgid AS msgid_singular,
    msgid_plural.msgid AS msgid_plural 
FROM
    potmsgset
    JOIN translationtemplateitem ON
         translationtemplateitem.potmsgset = potmsgset.id
    JOIN potemplate ON
         potemplate.id = translationtemplateitem.potemplate
    LEFT JOIN pomsgid msgid_singular ON
          potmsgset.msgid_singular = msgid_singular.id
    LEFT JOIN pomsgid msgid_plural ON
          potmsgset.msgid_plural = msgid_plural.id;

-- Replace POExport with a view going through TranslationTemplateItem,
-- and adding a translationmessage.diverged value.
DROP VIEW poexport;
CREATE VIEW poexport AS
    SELECT
      ((COALESCE((potmsgset.id)::text, 'X'::text) || '.'::text) || COALESCE((translationmessage.id)::text, 'X'::text)) AS id,
      potemplate.productseries,
      potemplate.sourcepackagename,
      potemplate.distroseries,
      potemplate.id AS potemplate,
      potemplate.header AS template_header,
      potemplate.languagepack,
      pofile.id AS pofile,
      pofile.language,
      pofile.variant,
      pofile.topcomment AS translation_file_comment,
      pofile.header AS translation_header,
      pofile.fuzzyheader AS is_translation_header_fuzzy,
      translationtemplateitem.sequence,
      potmsgset.id AS potmsgset,
      translationmessage.comment,
      potmsgset.sourcecomment AS source_comment,
      potmsgset.filereferences AS file_references,
      potmsgset.flagscomment AS flags_comment,
      potmsgset.context,
      msgid_singular.msgid AS msgid_singular,
      msgid_plural.msgid AS msgid_plural,
      translationmessage.is_current,
      translationmessage.is_imported,
      translationmessage.potemplate AS diverged,
      potranslation0.translation AS translation0,
      potranslation1.translation AS translation1,
      potranslation2.translation AS translation2,
      potranslation3.translation AS translation3,
      potranslation4.translation AS translation4,
      potranslation5.translation AS translation5
FROM
     potmsgset
     JOIN translationtemplateitem ON
          translationtemplateitem.potmsgset = potmsgset.id
     JOIN potemplate ON
          potemplate.id = translationtemplateitem.potemplate
     JOIN pofile ON
          potemplate.id = pofile.potemplate
     LEFT JOIN translationmessage ON
          (potmsgset.id = translationmessage.potmsgset AND
           translationmessage.is_current IS TRUE AND
           translationmessage.language = pofile.language AND
           translationmessage.variant IS NOT DISTINCT FROM pofile.variant)
     LEFT JOIN pomsgid msgid_singular ON
          msgid_singular.id = potmsgset.msgid_singular
     LEFT JOIN pomsgid msgid_plural ON
          msgid_plural.id = potmsgset.msgid_plural
     LEFT JOIN potranslation potranslation0 ON
          potranslation0.id = translationmessage.msgstr0
     LEFT JOIN potranslation potranslation1 ON
          potranslation1.id = translationmessage.msgstr1
     LEFT JOIN potranslation potranslation2 ON
          potranslation2.id = translationmessage.msgstr2
     LEFT JOIN potranslation potranslation3 ON
          potranslation3.id = translationmessage.msgstr3
     LEFT JOIN potranslation potranslation4 ON
          potranslation4.id = translationmessage.msgstr4
     LEFT JOIN potranslation potranslation5 ON
          potranslation5.id = translationmessage.msgstr5;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 48, 0);
