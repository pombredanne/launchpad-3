SET client_min_messages=ERROR;

-- fix the view so it works with POFiles that does not have any POMsgSet

DROP VIEW POExport;

CREATE OR REPLACE VIEW POExport AS SELECT
    coalesce(potmsgset.id::text, 'X') || '.' ||
    coalesce(pomsgset.id::text, 'X') || '.' ||
    coalesce(pomsgidsighting.id::text, 'X') || '.' ||
    coalesce(poselection.id::text, 'X') AS id,
    potemplatename.name,
    potemplatename.translationdomain,
    potemplate.id AS potemplate,
    potemplate.productrelease,
    potemplate.sourcepackagename,
    potemplate.distrorelease,
    potemplate.header AS potheader,
    potemplate.languagepack,
    pofile.id AS pofile,
    pofile.language,
    pofile.variant,
    pofile.topcomment AS potopcomment,
    pofile.header AS poheader,
    pofile.fuzzyheader AS pofuzzyheader,
    pofile.pluralforms AS popluralforms,
    potmsgset.id AS potmsgset,
    potmsgset.sequence AS potsequence,
    potmsgset.commenttext AS potcommenttext,
    potmsgset.sourcecomment,
    potmsgset.flagscomment,
    potmsgset.filereferences,
    pomsgset.id AS pomsgset,
    pomsgset.sequence AS posequence,
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
    JOIN pomsgidsighting
        ON pomsgid.id = pomsgidsighting.pomsgid
    JOIN potmsgset
        ON potmsgset.id = pomsgidsighting.potmsgset
    JOIN potemplate
        ON potemplate.id = potmsgset.potemplate
    JOIN potemplatename
        ON potemplatename.id = potemplate.potemplatename
    JOIN pofile
        ON potemplate.id = pofile.potemplate
    LEFT OUTER JOIN pomsgset
        ON potmsgset.id = pomsgset.potmsgset AND pomsgset.pofile = pofile.id
    LEFT OUTER JOIN poselection
        ON pomsgset.id = poselection.pomsgset
    LEFT OUTER JOIN posubmission
        ON posubmission.id = poselection.activesubmission
    LEFT OUTER JOIN potranslation
        ON potranslation.id = posubmission.potranslation;

INSERT INTO LaunchpadDatabaseRevision VALUES (17,21,2);
