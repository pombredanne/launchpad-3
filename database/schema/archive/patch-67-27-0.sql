SET client_min_messages=ERROR;

-- Change the POExport view to stop using POFile.pluralforms field

DROP VIEW POExport;

CREATE OR REPLACE VIEW POExport AS
SELECT ((((((COALESCE((potmsgset.id)::text, 'X'::text) || '.'::text) ||
    COALESCE((pomsgset.id)::text, 'X'::text)) || '.'::text) ||
    COALESCE((pomsgidsighting.id)::text, 'X'::text)) || '.'::text) ||
    COALESCE((poselection.id)::text, 'X'::text)) AS id,
    potemplatename.name,
    potemplatename.translationdomain,
    potemplate.id AS potemplate,
    potemplate.productseries,
    potemplate.sourcepackagename,
    potemplate.distrorelease,
    potemplate."header" AS potheader,
    potemplate.languagepack,
    pofile.id AS pofile,
    pofile."language",
    pofile.variant,
    pofile.topcomment AS potopcomment,
    pofile."header" AS poheader,
    pofile.fuzzyheader AS pofuzzyheader,
    potmsgset.id AS potmsgset,
    potmsgset."sequence" AS potsequence,
    potmsgset.commenttext AS potcommenttext,
    potmsgset.sourcecomment,
    potmsgset.flagscomment,
    potmsgset.filereferences,
    pomsgset.id AS pomsgset,
    pomsgset."sequence" AS posequence,
    pomsgset.iscomplete,
    pomsgset.obsolete,
    pomsgset.isfuzzy,
    pomsgset.commenttext AS pocommenttext,
    pomsgidsighting.pluralform AS msgidpluralform,
    poselection.pluralform AS translationpluralform,
    poselection.activesubmission,
    pomsgid.msgid,
    potranslation.translation
FROM
    pomsgid
        JOIN pomsgidsighting ON pomsgid.id = pomsgidsighting.pomsgid
        JOIN potmsgset ON potmsgset.id = pomsgidsighting.potmsgset
        JOIN potemplate ON potemplate.id = potmsgset.potemplate
        JOIN potemplatename ON potemplatename.id = potemplate.potemplatename
        JOIN pofile ON potemplate.id = pofile.potemplate
        LEFT JOIN pomsgset ON
            (potmsgset.id = pomsgset.potmsgset) AND
            (pomsgset.pofile = pofile.id)
        LEFT JOIN poselection ON pomsgset.id = poselection.pomsgset
        LEFT JOIN posubmission ON posubmission.id = poselection.activesubmission
        LEFT JOIN potranslation ON potranslation.id = posubmission.potranslation;

ALTER TABLE POFile DROP COLUMN pluralforms;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 27, 0);
