SET client_min_messages=ERROR;

-- Relax database constraints for message-sharing.

-- POTMsgSet table changes.
-- Removes pointer to POTemplate from POTMsgSet table indexes.

DROP INDEX potmsgset__potemplate__context__msgid_singular__msgid_plural__k;
CREATE INDEX potmsgset__context__msgid_singular__msgid_plural__key ON potmsgset USING btree (context, msgid_singular, msgid_plural) WHERE ((context IS NOT NULL) AND (msgid_plural IS NOT NULL));

DROP INDEX potmsgset__potemplate__context__msgid_singular__no_msgid_plural;
CREATE INDEX potmsgset__context__msgid_singular__no_msgid_plural__idx ON potmsgset USING btree (context, msgid_singular) WHERE ((context IS NOT NULL) AND (msgid_plural IS NULL));

DROP INDEX potmsgset__potemplate__no_context__msgid_singular__msgid_plural;
CREATE INDEX potmsgset__no_context__msgid_singular__msgid_plural__idx ON potmsgset USING btree (msgid_singular, msgid_plural) WHERE ((context IS NULL) AND (msgid_plural IS NOT NULL));

DROP INDEX potmsgset__potemplate__no_context__msgid_singular__no_msgid_plu;
CREATE INDEX potmsgset__no_context__msgid_singular__no_msgid_plural__idx ON potmsgset USING btree (msgid_singular) WHERE ((context IS NULL) AND (msgid_plural IS NULL));

-- Set up a replacement index on TranslationTemplateItem.
DROP INDEX potmsgset_potemplate_and_sequence_idx;
CREATE INDEX translationtemplateitem__potemplate__potmsgset__sequence__idx ON translationtemplateitem USING btree (potemplate, potmsgset, sequence);

-- Replace constraint with one allowing sequence of zero.
ALTER TABLE TranslationTemplateItem DROP CONSTRAINT translationtemplateitem_sequence_check;
ALTER TABLE TranslationTemplateItem ADD CONSTRAINT translationtemplateitem_sequence_check CHECK (sequence >= 0);


ALTER TABLE potmsgset ALTER COLUMN potemplate DROP NOT NULL;

ALTER TABLE potmsgset ALTER COLUMN sequence DROP NOT NULL;

-- TranslationMessage table changes.
-- Removes pointers to PO file and replaces them with (language, variant) pair.
-- Also provides for shared (potemplate IS NULL) and
-- diverged (potemplate IS NOT NULL).

ALTER TABLE translationmessage ALTER COLUMN pofile DROP NOT NULL;

DROP INDEX translationmessage__pofile__potmsgset__msgstrs__key;
CREATE UNIQUE INDEX translationmessage__language__variant__potmsgset__shared__msgstrs__key ON translationmessage USING btree (language, variant, potmsgset, (COALESCE(msgstr0, -1)), (COALESCE(msgstr1, -1)), (COALESCE(msgstr2, -1)), (COALESCE(msgstr3, -1)), (COALESCE(msgstr4, -1)), (COALESCE(msgstr5, -1))) WHERE (potemplate IS NULL);
CREATE UNIQUE INDEX translationmessage__language__variant__potmsgset__diverged__msgstrs__key ON translationmessage USING btree (language, variant, potmsgset, (COALESCE(msgstr0, -1)), (COALESCE(msgstr1, -1)), (COALESCE(msgstr2, -1)), (COALESCE(msgstr3, -1)), (COALESCE(msgstr4, -1)), (COALESCE(msgstr5, -1))) WHERE (potemplate IS NOT NULL);

DROP INDEX translationmessage__pofile__submitter__idx;
CREATE INDEX translationmessage__language__submitter__idx ON translationmessage USING btree (language, submitter);

DROP INDEX translationmessage__potmsgset__pofile__is_current__key;
CREATE UNIQUE INDEX translationmessage__potmsgset__language__variant__shared__current__key ON translationmessage USING btree (potmsgset, language, variant) WHERE ((is_current IS TRUE) AND (potemplate IS NULL));
CREATE UNIQUE INDEX translationmessage__potmsgset__language__variant__diverged__current__key ON translationmessage USING btree (potmsgset, language, variant) WHERE ((is_current IS TRUE) AND (potemplate IS NOT NULL));

DROP INDEX translationmessage__potmsgset__pofile__is_imported__key;
-- There can be only a single shared translation to a language/variant
-- for a POTMsgSet.
CREATE UNIQUE INDEX translationmessage__potmsgset__language__variant__shared__imported__key ON translationmessage USING btree (potmsgset, language, variant) WHERE ((is_imported IS TRUE) AND (potemplate IS NULL));
-- Diverged translations need not be unique.
CREATE INDEX translationmessage__potmsgset__language__variant__diverged__imported__key ON translationmessage USING btree (potmsgset, language, variant) WHERE ((is_imported IS TRUE) AND (potemplate IS NOT NULL));

DROP INDEX translationmessage__potmsgset__pofile__not_used__key;
CREATE INDEX translationmessage__potmsgset__language__variant__not_used__key ON translationmessage USING btree (potmsgset, language, variant) WHERE (NOT ((is_current IS TRUE) AND (is_imported IS TRUE)));

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
      potmsgset.sequence,
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
           translationmessage.pofile = pofile.id AND
           translationmessage.is_current IS TRUE)
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

DROP VIEW potexport;
CREATE VIEW potexport AS
    SELECT COALESCE((potmsgset.id)::text, 'X'::text) AS id,
    potemplate.productseries,
    potemplate.sourcepackagename,
    potemplate.distroseries,
    potemplate.id AS potemplate,
    potemplate.header AS template_header,
    potemplate.languagepack,
    potmsgset.sequence,
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


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
