SET client_min_messages=ERROR;

DROP VIEW IF EXISTS POExport;

CREATE VIEW POExport AS
SELECT
  ((COALESCE((potmsgset.id)::text, 'X'::text) || '.'::text) || COALESCE((translationmessage.id)::text, 'X'::text)) AS id,
  POTemplate.productseries,
  POTemplate.sourcepackagename,
  POTemplate.distroseries,
  POTemplate.id AS potemplate,
  POTemplate.header AS template_header,
  POTemplate.languagepack,
  POFile.id AS pofile,
  POFile.language,
  POFile.variant,
  POFile.topcomment AS translation_file_comment,
  POFile.header AS translation_header,
  POFile.fuzzyheader AS is_translation_header_fuzzy,
  TranslationTemplateItem.sequence,
  POTMsgSet.id AS potmsgset,
  TranslationMessage.comment,
  POTMsgSet.sourcecomment AS source_comment,
  POTMsgSet.filereferences AS file_references,
  POTMsgSet.flagscomment AS flags_comment,
  POTMsgSet.context,
  msgid_singular.msgid AS msgid_singular,
  msgid_plural.msgid AS msgid_plural,
  TranslationMessage.is_current,
  TranslationMessage.is_imported,
  TranslationMessage.potemplate AS diverged,
  potranslation0.translation AS translation0,
  potranslation1.translation AS translation1,
  potranslation2.translation AS translation2,
  potranslation3.translation AS translation3,
  potranslation4.translation AS translation4,
  potranslation5.translation AS translation5
FROM POTMsgSet
JOIN TranslationTemplateItem ON
    TranslationTemplateItem.potmsgset = POTMsgSet.id
JOIN POTemplate ON
    POTemplate.id = TranslationTemplateItem.potemplate
JOIN POFile ON
    POTemplate.id = POFile.potemplate
LEFT JOIN TranslationMessage ON
    POTMsgSet.id = TranslationMessage.potmsgset AND
    TranslationMessage.is_current IS TRUE AND
    TranslationMessage.language = POFile.language AND
    TranslationMessage.variant IS NOT DISTINCT FROM POFile.variant
LEFT JOIN POMsgID AS msgid_singular ON
    msgid_singular.id = POTMsgSet.msgid_singular
LEFT JOIN POMsgID AS msgid_plural ON
    msgid_plural.id = POTMsgSet.msgid_plural
LEFT JOIN POTranslation AS potranslation0 ON
    potranslation0.id = TranslationMessage.msgstr0
LEFT JOIN POTranslation AS potranslation1 ON
    potranslation1.id = TranslationMessage.msgstr1
LEFT JOIN POTranslation AS potranslation2 ON
    potranslation2.id = TranslationMessage.msgstr2
LEFT JOIN POTranslation AS potranslation3 ON
    potranslation3.id = TranslationMessage.msgstr3
LEFT JOIN POTranslation AS potranslation4 ON
    potranslation4.id = TranslationMessage.msgstr4
LEFT JOIN POTranslation potranslation5 ON
    potranslation5.id = TranslationMessage.msgstr5
WHERE
    TranslationMessage.potemplate IS NULL OR
    TranslationMessage.potemplate = POFile.potemplate;


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 61, 1);
