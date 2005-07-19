
set client_min_messages=ERROR;

/* we would like to link all upstream templates to series, rather than
 * product release */

ALTER TABLE POTemplate ADD COLUMN ProductSeries integer;
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_productseries_fk
    FOREIGN KEY (productseries) REFERENCES ProductSeries(id);

UPDATE POTemplate SET productseries=ProductRelease.productseries FROM
ProductRelease WHERE POTemplate.productrelease=ProductRelease.id;

ALTER TABLE POTemplate ADD CONSTRAINT potemplate_productseries_ptname_uniq UNIQUE
(productseries, potemplatename);
ALTER TABLE POTemplate DROP CONSTRAINT valid_link;
ALTER TABLE POTemplate ADD CONSTRAINT "valid_link" CHECK ((productseries IS
NULL) <> (distrorelease IS NULL) AND
(distrorelease IS NULL) = (sourcepackagename IS NULL));

-- update the poexport view to work with productseries

DROP VIEW POExport;

CREATE OR REPLACE VIEW POExport AS
    SELECT (((((COALESCE(potmsgset.id::text, 'X'::text) || '.'::text) ||
    COALESCE(pomsgset.id::text, 'X'::text)) || '.'::text) ||
    COALESCE(pomsgidsighting.id::text, 'X'::text)) || '.'::text) ||
    COALESCE(poselection.id::text, 'X'::text) AS id,
    potemplatename.name,
    potemplatename.translationdomain,
    potemplate.id AS potemplate,
    potemplate.productseries,
    potemplate.sourcepackagename,
    potemplate.distrorelease,
    potemplate.header AS potheader,
    potemplate.languagepack,
    pofile.id AS pofile,
    pofile."language",
    pofile.variant,
    pofile.topcomment AS potopcomment,
    pofile.header AS
    poheader,
    pofile.fuzzyheader AS pofuzzyheader,
    pofile.pluralforms AS popluralforms,
    potmsgset.id AS potmsgset,
    potmsgset."sequence" AS
    potsequence,
    potmsgset.commenttext AS potcommenttext,
    potmsgset.sourcecomment,
    potmsgset.flagscomment,
    potmsgset.filereferences, pomsgset.id AS pomsgset,
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
FROM pomsgid
    JOIN pomsgidsighting ON pomsgid.id = pomsgidsighting.pomsgid
    JOIN potmsgset ON potmsgset.id = pomsgidsighting.potmsgset
    JOIN potemplate ON potemplate.id = potmsgset.potemplate
    JOIN potemplatename ON potemplatename.id = potemplate.potemplatename
    JOIN pofile ON potemplate.id = pofile.potemplate
    LEFT JOIN pomsgset ON potmsgset.id = pomsgset.potmsgset AND
                          pomsgset.pofile = pofile.id
    LEFT JOIN poselection ON pomsgset.id = poselection.pomsgset
    LEFT JOIN posubmission ON posubmission.id = poselection.activesubmission
    LEFT JOIN potranslation ON potranslation.id = posubmission.potranslation;
       

ALTER TABLE POTemplate DROP COLUMN productrelease;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 40, 0);

