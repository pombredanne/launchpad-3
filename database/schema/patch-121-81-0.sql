SET client_min_messages=ERROR;

UPDATE TranslationMessage
  SET is_current=FALSE, is_fuzzy=FALSE
  WHERE (
    is_current IS TRUE AND
    is_imported IS FALSE AND
    is_fuzzy IS TRUE);

DELETE FROM TranslationMessage
  WHERE is_fuzzy IS TRUE;

DROP VIEW POExport;
CREATE VIEW POExport(
    id,
    productseries,
    sourcepackagename,
    distroseries,
    potemplate,
    template_header,
    languagepack,
    pofile,
    language,
    variant,
    translation_file_comment,
    translation_header,
    is_translation_header_fuzzy,
    sequence,
    potmsgset,
    "comment",
    source_comment,
    file_references,
    flags_comment,
    context,
    msgid_singular,
    msgid_plural,
    is_current,
    is_imported,
    translation0,
    translation1,
    translation2,
    translation3,
    translation4,
    translation5
    ) AS
SELECT
    COALESCE(potmsgset.id::text, 'X'::text) || '.'::text || COALESCE(translationmessage.id::text, 'X'::text) AS id,
    potemplate.productseries,
    potemplate.sourcepackagename,
    potemplate.distroseries,
    potemplate.id AS potemplate,
    potemplate."header" AS template_theader,
    potemplate.languagepack,
    pofile.id AS pofile,
    pofile."language",
    pofile.variant,
    pofile.topcomment AS translation_file_comment,
    pofile."header" AS translation_header,
    pofile.fuzzyheader AS is_translation_header_fuzzy,
    potmsgset."sequence",
    potmsgset.id AS potmsgset,
    translationmessage.comment AS "comment",
    potmsgset.sourcecomment AS source_comment,
    potmsgset.filereferences AS file_references,
    potmsgset.flagscomment AS flags_comment,
    potmsgset.context,
    msgid_singular.msgid AS msgid_singular,
    msgid_plural.msgid AS msgid_plural,
    translationmessage.is_current,
    translationmessage.is_imported,
    potranslation0.translation AS translation0,
    potranslation1.translation AS translation1,
    potranslation2.translation AS translation2,
    potranslation3.translation AS translation3,
    potranslation4.translation AS translation4,
    potranslation5.translation AS translation5
FROM
    potmsgset
        JOIN potemplate ON potemplate.id = potmsgset.potemplate
        JOIN pofile ON potemplate.id = pofile.potemplate
        LEFT JOIN TranslationMessage ON
            potmsgset.id = translationmessage.potmsgset AND
            translationmessage.pofile = pofile.id AND
            translationmessage.is_current IS TRUE
        LEFT JOIN pomsgid AS msgid_singular ON
            msgid_singular.id = potmsgset.msgid_singular
        LEFT JOIN pomsgid AS msgid_plural ON
            msgid_plural.id = potmsgset.msgid_plural
        LEFT JOIN potranslation AS potranslation0 ON
            potranslation0.id = translationmessage.msgstr0
        LEFT JOIN potranslation AS potranslation1 ON
            potranslation1.id = translationmessage.msgstr1
        LEFT JOIN potranslation AS potranslation2 ON
            potranslation2.id = translationmessage.msgstr2
        LEFT JOIN potranslation AS potranslation3 ON
            potranslation3.id = translationmessage.msgstr3
        LEFT JOIN potranslation AS potranslation4 ON
            potranslation4.id = translationmessage.msgstr4
        LEFT JOIN potranslation AS potranslation5 ON
            potranslation5.id = translationmessage.msgstr5;



INSERT INTO LaunchpadDatabaseRevision VALUES (121, 81, 0);
