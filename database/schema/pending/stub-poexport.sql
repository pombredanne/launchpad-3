CREATE OR REPLACE VIEW POExport AS SELECT
    potemplate.id,
    potemplate.product,
    pofile.language,
    potemplate.name, potemplate.header AS potheader,
    pomsgset.id AS pomsgsetid,
    potmsgset.id AS potmsgsetid,
    pofile.topcomment,
    pofile.header,
    pofile.fuzzyheader,
    pofile.pluralforms,
    pofile.variant,
    potmsgset.sequence AS potsequence,
    potmsgset.commenttext AS potcommenttext,
    potmsgset.sourcecomment,
    potmsgset.flagscomment,
    pomsgset.sequence AS posequence,
    pomsgset.iscomplete,
    pomsgset.obsolete,
    pomsgset.fuzzy,
    pomsgset.commenttext AS pocommenttext,
    pomsgidsighting.pluralform AS popluralform,
    potranslationsighting.pluralform AS potpluralform,
    potranslationsighting.active,
    pomsgid.msgid,
    potranslation.translation
FROM
    potemplate, pomsgidsighting, pomsgid, pofile,
    potmsgset LEFT OUTER JOIN (
        pomsgset LEFT OUTER JOIN (
            potranslationsighting LEFT OUTER JOIN potranslation
                ON potranslationsighting.potranslation = potranslation.id
            ) ON potranslationsighting.pomsgset = pomsgset.id
        ) ON potmsgset.id = pomsgset.potmsgset
WHERE
    potemplate.id = potmsgset.potemplate
    AND (pomsgset.id IS NULL OR pomsgset.pofile = pofile.id)
    AND potmsgset.id = pomsgidsighting.potmsgset
    AND pomsgid.id = pomsgidsighting.pomsgid
    AND potemplate.id = pofile.potemplate;

ALTER TABLE pofile DROP CONSTRAINT pofile_id_key;

CREATE INDEX potranslationsighting_potranslation_idx
    ON potranslationsighting(potranslation);
CREATE INDEX pofile_potemplate_idx ON pofile(potemplate);
CREATE INDEX pofile_language_idx ON pofile(language);
