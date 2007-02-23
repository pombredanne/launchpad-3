SET client_min_messages=ERROR;
DROP VIEW POExport;
ALTER TABLE POFile DROP COLUMN latestsubmission;
ALTER TABLE POSubmission DISABLE TRIGGER mv_pofiletranslator_posubmission;
ALTER TABLE POMsgSet DISABLE TRIGGER mv_pofiletranslator_pomsgset;
DELETE FROM POFileTranslator;
ALTER TABLE POFileTranslator DROP CONSTRAINT personpofile__latest_posubmission__fk;

CREATE TABLE POMsgSetNew (
    id serial NOT NULL,
    "sequence" integer NOT NULL,
    pofile integer NOT NULL,
    iscomplete boolean NOT NULL,
    obsolete boolean NOT NULL,
    isfuzzy boolean NOT NULL,
    commenttext text,
    potmsgset integer NOT NULL,
    publishedfuzzy boolean DEFAULT false NOT NULL,
    publishedcomplete boolean DEFAULT false NOT NULL,
    isupdated boolean DEFAULT false NOT NULL,
    date_reviewed TIMESTAMP WITHOUT TIME ZONE,
    reviewer INTEGER
);

INSERT INTO POMsgSetNew(
    id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext,
    potmsgset, publishedfuzzy, publishedcomplete, isupdated, date_reviewed,
    reviewer)
SELECT
    pms.id,
    pms."sequence",
    pms.pofile,
    pms.iscomplete,
    pms.obsolete,
    pms.isfuzzy,
    pms.commenttext,
    pms.potmsgset,
    pms.publishedfuzzy,
    pms.publishedcomplete,
    pms.isupdated,
    psel.date_reviewed,
    psel.reviewer
FROM
    POMsgSet AS pms
    LEFT JOIN (
    SELECT DISTINCT ON (pomsgset) id, pomsgset, date_reviewed, reviewer
    FROM POSelection
    ORDER BY pomsgset, date_reviewed DESC
    ) AS psel ON pms.id = psel.pomsgset;

SELECT setval('pomsgsetnew_id_seq', (SELECT last_value FROM pomsgset_id_seq), TRUE);

CREATE TABLE POSubmissionNew (
    id serial NOT NULL,
    pomsgset integer NOT NULL,
    pluralform integer NOT NULL,
    potranslation integer NOT NULL,
    origin integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer NOT NULL,
    validationstatus integer DEFAULT 0 NOT NULL,
    active BOOLEAN DEFAULT FALSE NOT NULL,
    published BOOLEAN DEFAULT FALSE NOT NULL,
    CONSTRAINT posubmission_valid_pluralform CHECK ((pluralform >= 0))
);


INSERT INTO POSubmissionNew(
    id, pomsgset, pluralform, potranslation, origin, datecreated, person,
    validationstatus, active, published)
SELECT
    ps.id,
    ps.pomsgset,
    ps.pluralform,
    ps.potranslation,
    ps.origin,
    ps.datecreated,
    ps.person,
    ps.validationstatus,
    COALESCE(psel.activesubmission = ps.id, FALSE),
    COALESCE(psel.publishedsubmission = ps.id, FALSE)
FROM
    POSubmission AS ps
    LEFT JOIN POSelection AS psel ON
        psel.pomsgset = ps.pomsgset AND
        psel.pluralform = ps.pluralform;

SELECT setval('posubmissionnew_id_seq', (SELECT last_value FROM posubmission_id_seq), TRUE);

DROP TABLE POSelection;
DROP TABLE POSubmission;
DROP TABLE POMsgSet;
ALTER TABLE POSubmissionNew RENAME TO POSubmission;
ALTER TABLE POMsgSetNew RENAME TO POMsgSet;

-- Feisty opening.
INSERT INTO POTemplate (
    description, path, iscurrent, messagecount, owner,
    sourcepackagename, distrorelease, header, potemplatename,
    binarypackagename, languagepack, from_sourcepackagename,
    date_last_updated, priority)
SELECT
    pt.description AS description,
    pt.path AS path,
    pt.iscurrent AS iscurrent,
    pt.messagecount AS messagecount,
    pt.owner AS owner,
    pt.sourcepackagename AS sourcepackagename,
    dr.id AS distrorelease,
    pt.header AS header,
    pt.potemplatename AS potemplatename,
    pt.binarypackagename AS binarypackagename,
    pt.languagepack AS languagepack,
    pt.from_sourcepackagename AS from_sourcepackagename,
    pt.date_last_updated AS date_last_updated,
    pt.priority AS priority
FROM
    POTemplate AS pt
    JOIN (
        SELECT DISTINCT ON (DistroRelease.id)
            DistroRelease.id, DistroRelease.name, DistroRelease.distribution,
            DistroRelease.parentrelease
        FROM DistroRelease, Distribution
        WHERE
            DistroRelease.name = 'feisty' AND
            DistroRelease.distribution = Distribution.id AND
            Distribution.name = 'ubuntu'
        ) AS dr ON parentrelease = pt.distrorelease
WHERE
    pt.iscurrent = TRUE;

INSERT INTO POTMsgSet (
    primemsgid, sequence, potemplate, commenttext,
    filereferences, sourcecomment, flagscomment)
SELECT
    ptms.primemsgid AS primemsgid,
    ptms.sequence AS sequence,
    pt2.id AS potemplate,
    ptms.commenttext AS commenttext,
    ptms.filereferences AS filereferences,
    ptms.sourcecomment AS sourcecomment,
    ptms.flagscomment AS flagscomment
FROM
    POTemplate AS pt1
    JOIN POTMsgSet AS ptms ON
        ptms.potemplate = pt1.id AND
        ptms.sequence > 0
    JOIN (
        SELECT DISTINCT ON (DistroRelease.id)
            DistroRelease.id, DistroRelease.name, DistroRelease.distribution,
            DistroRelease.parentrelease
        FROM DistroRelease, Distribution
        WHERE
            DistroRelease.name = 'feisty' AND
            DistroRelease.distribution = Distribution.id AND
            Distribution.name = 'ubuntu'
        ) AS dr ON parentrelease = pt1.distrorelease
    JOIN POTemplate AS pt2 ON
        pt2.distrorelease = dr.id AND
        pt2.potemplatename = pt1.potemplatename AND
        pt2.sourcepackagename = pt1.sourcepackagename;

INSERT INTO POMsgIDSighting (
    potmsgset, pomsgid, datefirstseen, datelastseen,
    inlastrevision, pluralform)
SELECT
    ptms2.id AS potmsgset,
    pmis.pomsgid AS pomsgid,
    pmis.datefirstseen AS datefirstseen,
    pmis.datelastseen AS datelastseen,
    pmis.inlastrevision AS inlastrevision,
    pmis.pluralform AS pluralform
FROM
    POTemplate AS pt1
    JOIN (
        SELECT DISTINCT ON (DistroRelease.id)
            DistroRelease.id, DistroRelease.name, DistroRelease.distribution,
            DistroRelease.parentrelease
        FROM DistroRelease, Distribution
        WHERE
            DistroRelease.name = 'feisty' AND
            DistroRelease.distribution = Distribution.id AND
            Distribution.name = 'ubuntu'
        ) AS dr ON pt1.distrorelease = dr.parentrelease
    JOIN POTMsgSet AS ptms1 ON
        ptms1.potemplate = pt1.id
    JOIN POTemplate AS pt2 ON
        pt2.distrorelease = dr.id AND
        pt2.potemplatename = pt1.potemplatename AND
        pt2.sourcepackagename = pt1.sourcepackagename
    JOIN POMsgIDSighting AS pmis ON
        pmis.potmsgset = ptms1.id
    JOIN POTMsgSet AS ptms2 ON
        ptms2.potemplate = pt2.id AND
        ptms1.primemsgid = ptms2.primemsgid;

INSERT INTO POFile (
    potemplate, language, description, topcomment, header,
    fuzzyheader, lasttranslator, currentcount, updatescount,
    rosettacount, lastparsed, owner, variant, path, exportfile,
    exporttime, datecreated, from_sourcepackagename)
SELECT
    pt2.id AS potemplate,
    pf1.language AS language,
    pf1.description AS description,
    pf1.topcomment AS topcomment,
    pf1.header AS header,
    pf1.fuzzyheader AS fuzzyheader,
    pf1.lasttranslator AS lasttranslator,
    pf1.currentcount AS currentcount,
    pf1.updatescount AS updatescount,
    pf1.rosettacount AS rosettacount,
    pf1.lastparsed AS lastparsed,
    pf1.owner AS owner,
    pf1.variant AS variant,
    pf1.path AS path,
    pf1.exportfile AS exportfile,
    pf1.exporttime AS exporttime,
    pf1.datecreated AS datecreated,
    pf1.from_sourcepackagename AS from_sourcepackagename
FROM
    POTemplate AS pt1
    JOIN (
        SELECT DISTINCT ON (DistroRelease.id)
            DistroRelease.id, DistroRelease.name, DistroRelease.distribution,
            DistroRelease.parentrelease
        FROM DistroRelease, Distribution
        WHERE
            DistroRelease.name = 'feisty' AND
            DistroRelease.distribution = Distribution.id AND
            Distribution.name = 'ubuntu'
        ) AS dr ON pt1.distrorelease = dr.parentrelease
    JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
    JOIN POTemplate AS pt2 ON
        pt2.potemplatename = pt1.potemplatename AND
        pt2.sourcepackagename = pt1.sourcepackagename AND
        pt2.distrorelease = dr.id;

ALTER TABLE ONLY POMsgSet
    ADD CONSTRAINT pomsgset__potmsgset__pofile__key UNIQUE (potmsgset, pofile);

INSERT INTO POMsgSet (
    sequence, pofile, iscomplete, obsolete, isfuzzy, commenttext,
    potmsgset, publishedfuzzy, publishedcomplete, isupdated, reviewer,
    date_reviewed)
SELECT
    pms1.sequence AS sequence,
    pf2.id AS pofile,
    pms1.iscomplete AS iscomplete,
    pms1.obsolete AS obsolete,
    pms1.isfuzzy AS isfuzzy,
    pms1.commenttext AS commenttext,
    ptms2.id AS potmsgset,
    pms1.publishedfuzzy AS publishedfuzzy,
    pms1.publishedcomplete AS publishedcomplete,
    pms1.isupdated AS isupdated,
    pms1.reviewer AS reviewer,
    pms1.date_reviewed AS date_reviewed
FROM
    POTemplate AS pt1
    JOIN (
        SELECT DISTINCT ON (DistroRelease.id)
            DistroRelease.id, DistroRelease.name, DistroRelease.distribution,
            DistroRelease.parentrelease
        FROM DistroRelease, Distribution
        WHERE
            DistroRelease.name = 'feisty' AND
            DistroRelease.distribution = Distribution.id AND
            Distribution.name = 'ubuntu'
        ) AS dr ON pt1.distrorelease = dr.parentrelease
    JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
    JOIN POTemplate AS pt2 ON
        pt2.potemplatename = pt1.potemplatename AND
        pt2.sourcepackagename = pt1.sourcepackagename AND
        pt2.distrorelease = dr.id
    JOIN POFile AS pf2 ON
        pf2.potemplate = pt2.id AND
        pf2.language = pf1.language AND
        (pf2.variant = pf1.variant OR
         (pf2.variant IS NULL AND pf1.variant IS NULL))
    JOIN POTMsgSet AS ptms1 ON ptms1.potemplate = pt1.id
    JOIN POMsgSet AS pms1 ON
        pms1.potmsgset = ptms1.id AND
        pms1.pofile = pf1.id
    JOIN POTMsgSet AS ptms2 ON
        ptms2.potemplate = pt2.id AND
        ptms2.primemsgid = ptms1.primemsgid;

CREATE INDEX posubmission__pomsgset__pluralform__active__idx
    ON POSubmission (pomsgset, pluralform, active);
CREATE INDEX posubmission__pomsgset__pluralform__published__idx
    ON POSubmission (pomsgset, pluralform, published);

INSERT INTO POSubmission (
    pomsgset, pluralform, potranslation, origin, datecreated,
    person, validationstatus, active, published)
SELECT
    pms2.id AS pomsgset,
    ps1.pluralform AS pluralform,
    ps1.potranslation AS potranslation,
    ps1.origin AS origin,
    ps1.datecreated AS datecreated,
    ps1.person AS person,
    ps1.validationstatus AS validationstatus,
    ps1.active,
    ps1.published
FROM
    POTemplate AS pt1
    JOIN (
        SELECT DISTINCT ON (DistroRelease.id)
            DistroRelease.id, DistroRelease.name, DistroRelease.distribution,
            DistroRelease.parentrelease
        FROM DistroRelease, Distribution
        WHERE
            DistroRelease.name = 'feisty' AND
            DistroRelease.distribution = Distribution.id AND
            Distribution.name = 'ubuntu'
        ) AS dr ON pt1.distrorelease = dr.parentrelease
    JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
    JOIN POTemplate AS pt2 ON
        pt2.potemplatename = pt1.potemplatename AND
        pt2.sourcepackagename = pt1.sourcepackagename AND
        pt2.distrorelease = dr.id
    JOIN POFile AS pf2 ON
        pf2.potemplate = pt2.id AND
        pf2.language = pf1.language AND
        (pf2.variant = pf1.variant OR
         (pf2.variant IS NULL AND pf1.variant IS NULL))
    JOIN POTMsgSet AS ptms1 ON ptms1.potemplate = pt1.id
    JOIN POMsgSet AS pms1 ON
        pms1.potmsgset = ptms1.id AND
        pms1.pofile = pf1.id
    JOIN POTMsgSet AS ptms2 ON
        ptms2.potemplate = pt2.id AND
        ptms2.primemsgid = ptms1.primemsgid
    JOIN POMsgSet AS pms2 ON
        pms2.potmsgset = ptms2.id AND
        pms2.pofile = pf2.id
    JOIN POSubmission AS ps1 ON
        ps1.pomsgset = pms1.id AND
        (ps1.active OR ps1.published);

-- pomsgset constraints:
ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_pkey PRIMARY KEY (id);
ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset__pofile__fk FOREIGN KEY (pofile) REFERENCES pofile(id);
ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset__potmsgset__fk FOREIGN KEY (potmsgset) REFERENCES potmsgset(id);
ALTER TABLE POMsgSet ADD CONSTRAINT pomsgset__reviewer__date_reviewed__valid CHECK (
    reviewer IS NULL = date_reviewed IS NULL
    );
ALTER TABLE pomsgsetnew_id_seq RENAME TO pomsgset_id_seq;
ALTER TABLE pomsgset ALTER COLUMN id SET DEFAULT nextval('pomsgset_id_seq');


CREATE INDEX pomsgset__pofile__sequence__idx ON pomsgset USING btree (pofile, "sequence");
CREATE INDEX pomsgset__sequence__idx ON pomsgset USING btree ("sequence");
CREATE INDEX pomsgset__reviewer__idx ON POMsgSet (reviewer);

CREATE TRIGGER mv_pofiletranslator_pomsgset
    BEFORE DELETE OR UPDATE ON pomsgset
    FOR EACH ROW
    EXECUTE PROCEDURE mv_pofiletranslator_pomsgset();

-- posubmission restrictions
ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission__pomsgset__pluralform__id__key UNIQUE (pomsgset, pluralform, id);
ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission__potranslation__pomsgset__pluralform__key UNIQUE (potranslation, pomsgset, pluralform);
ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission__person__fk FOREIGN KEY (person) REFERENCES person(id);
ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission__potranslation__fk FOREIGN KEY (potranslation) REFERENCES potranslation(id);
ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission__pomsgset__fk FOREIGN KEY (pomsgset) REFERENCES pomsgset(id);
ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission_pkey PRIMARY KEY (id);
ALTER TABLE posubmissionnew_id_seq RENAME TO posubmission_id_seq;
ALTER TABLE posubmission ALTER COLUMN id
    SET DEFAULT nextval('posubmission_id_seq');

CREATE INDEX posubmission__person__idx ON posubmission USING btree (person);
CREATE UNIQUE INDEX posubmission__pomsgset__pluralform__active__unique_idx
    ON POSubmission (pomsgset, pluralform) WHERE active IS TRUE;
CREATE UNIQUE INDEX posubmission__pomsgset__pluralform__published__unique_idx
    ON POSubmission (pomsgset, pluralform) WHERE published IS TRUE;

CREATE TRIGGER mv_pofiletranslator_posubmission
    AFTER INSERT OR DELETE OR UPDATE ON posubmission
    FOR EACH ROW
    EXECUTE PROCEDURE mv_pofiletranslator_posubmission();

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

ALTER TABLE POFile ADD COLUMN last_touched_pomsgset
    INTEGER REFERENCES POMsgSet(id);

UPDATE POFile SET last_touched_pomsgset=pms.id
FROM (
    SELECT DISTINCT ON (pofile) id, pofile
    FROM POMsgSet
    WHERE POMsgSet.date_reviewed IS NOT NULL
    ORDER BY pofile, date_reviewed DESC
    ) AS pms
WHERE POFile.id = pms.pofile;

INSERT INTO POFileTranslator (
    person, pofile, latest_posubmission, date_last_touched
    )
    SELECT DISTINCT ON (POSubmission.person, POMsgSet.pofile)
        POSubmission.person, POMsgSet.pofile,
        POSubmission.id, POSubmission.datecreated
    FROM
        POSubmission, POMsgSet
    WHERE
        POSubmission.pomsgset = POMsgSet.id
    ORDER BY POSubmission.person, POMsgSet.pofile,
        POSubmission.datecreated DESC, POSubmission.id DESC;

ALTER TABLE ONLY pofiletranslator
    ADD CONSTRAINT personpofile__latest_posubmission__fk FOREIGN KEY (latest_posubmission) REFERENCES posubmission(id) DEFERRABLE INITIALLY DEFERRED;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 8, 0);
