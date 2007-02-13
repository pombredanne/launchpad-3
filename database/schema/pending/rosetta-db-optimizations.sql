SET client_min_messages=ERROR;

ALTER TABLE POSubmission ADD COLUMN active BOOLEAN DEFAULT FALSE NOT NULL;
UPDATE POSubmission SET active=TRUE FROM POSelection WHERE POSubmission.id = POSelection.activesubmission;

ALTER TABLE POSubmission ADD COLUMN published BOOLEAN DEFAULT FALSE NOT NULL;
UPDATE POSubmission SET published=TRUE FROM POSelection WHERE POSubmission.id = POSelection.publishedsubmission;

CREATE UNIQUE INDEX posubmission__pomsgset__pluralform__active__only_one_idx ON POSubmission (pomsgset, pluralform, NULLIF(active, FALSE));
CREATE UNIQUE INDEX posubmission__pomsgset__pluralform_published__only_one_idx ON POSubmission (pomsgset, pluralform, NULLIF(published, FALSE));

-- Do we still need this other INDEX ?
CREATE INDEX posubmission__pomsgset__pluralform__active__idx ON POSubmission(pomsgset, pluralform, active);
CREATE INDEX posubmission__pomsgset__pluralform__published__idx ON POSubmission(pomsgset, pluralform, published);

ALTER TABLE POMsgSet ADD COLUMN date_reviewed TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE POMsgSet ADD COLUMN reviewer INTEGER REFERENCES Person(id);
ALTER TABLE POMsgSet ADD CONSTRAINT review_fields_valid CHECK (reviewer IS NULL = date_reviewed IS NULL);
UPDATE POMsgSet SET date_reviewed = POSelection.date_reviewed, reviewer = POSelection.reviewer
FROM POSelection
WHERE POMsgSet.id = POSelection.pomsgset AND POSelection.id = (SELECT id FROM POSelection WHERE POSelection.pomsgset = POMsgset.id ORDER BY date_reviewed DESC LIMIT 1);

CREATE INDEX pomsgset__reviewer__idx ON POMsgSet(reviewer);

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
        LEFT JOIN posubmission ON
            pomsgset.id = posubmission.pomsgset AND
            posubmission.active
        LEFT JOIN potranslation ON potranslation.id = posubmission.potranslation;

ALTER TABLE POFile ADD COLUMN last_touched_pomsgset INTEGER REFERENCES POMsgSet(id);
UPDATE POFile SET last_touched_pomsgset=pms.id
FROM POMsgSet pms
WHERE pms.id = (
    SELECT id
    FROM POMsgSet
    WHERE POMsgSet.pofile = POFile.id AND POMsgSet.date_reviewed IS NOT NULL
    ORDER BY date_reviewed
    DESC
    LIMIT 1);

ALTER TABLE POFile DROP COLUMN latestsubmission;

DROP TABLE POSelection;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);
