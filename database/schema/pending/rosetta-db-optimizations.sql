SET client_min_messages=ERROR;

ALTER TABLE POSubmission ADD COLUMN active BOOLEAN DEFAULT FALSE NOT NULL;
update posubmission set active = true from poselection where posubmission.id = poselection.activesubmission;

ALTER TABLE POSubmission ADD COLUMN published BOOLEAN DEFAULT FALSE NOT NULL;
update posubmission set published = true from poselection where posubmission.id = poselection.publishedsubmission;


ALTER TABLE POSubmission ADD COLUMN date_reviewed TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE POSubmission ADD COLUMN reviewer INTEGER REFERENCES Person(id);
ALTER TABLE POSubmission ADD CONSTRAINT review_fields_valid CHECK (reviewer IS NULL = date_reviewed IS NULL);
UPDATE POSubmission SET date_reviewed = ps.date_reviewed, reviewer = ps.reviewer FROM POSelection ps WHERE ps.activesubmission = POSubmission.id;

CREATE INDEX posubmission__reviewer__idx ON POSubmission(reviewer);

CREATE UNIQUE INDEX posubmission__pomsgset__pluralform__active__only_one_idx ON POSubmission (pomsgset, pluralform, NULLIF(active, FALSE));
CREATE UNIQUE INDEX posubmission__pomsgset__pluralform_published__only_one_idx ON POSubmission (pomsgset, pluralform, NULLIF(published, FALSE));

-- Do we still need this other INDEX ?
CREATE INDEX posubmission__pomsgset__pluralform__active__idx ON POSubmission(pomsgset, pluralform, active);
CREATE INDEX posubmission__pomsgset__pluralform__published__idx ON POSubmission(pomsgset, pluralform, published);

DROP VIEW POExport;

CREATE OR REPLACE VIEW POExport AS
SELECT ((((((COALESCE((potmsgset.id)::text, 'X'::text) || '.'::text) ||
    COALESCE((pomsgset.id)::text, 'X'::text)) || '.'::text) ||
    COALESCE((pomsgidsighting.id)::text, 'X'::text)) || '.'::text) ||
    COALESCE((posubmission.id)::text, 'X'::text)) AS id,
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
    posubmission.pluralform AS translationpluralform,
    posubmission.id AS activesubmission,
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
        LEFT JOIN posubmission ON pomsgset.id = posubmission.pomsgset
        LEFT JOIN potranslation ON potranslation.id = posubmission.potranslation
WHERE posubmission.active = TRUE;

DROP TABLE POSelection;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);
