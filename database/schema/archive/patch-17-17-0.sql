
/* Refactor the translation sighting model to separate the idea of the
 * current published translations ("selections") from the submissions
 * themselves. This is an experimental branch by MarkShuttleworth to try to
 * clean up the core code in Rosetta and make it both more flexible and more
 * straightforward to maintain. */

SET client_min_messages=ERROR;

-- this is where the submission stuff goes. here we tell where it came from
-- and who provided it. this is also where licence stuff should go, once we
-- figure out how to track that
CREATE TABLE POSubmission (
    id                    serial NOT NULL, -- add primary key later
    pomsgset              integer NOT NULL,
    pluralform            integer NOT NULL,
    potranslation         integer NOT NULL,
    origin                integer NOT NULL,
    datecreated           timestamp without time zone NOT NULL
                          DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    person                integer,
    potranslationsighting integer NOT NULL -- temp cache
);


CREATE TABLE POSelection (
    id                   serial NOT NULL, -- add primary key later
    pomsgset             integer NOT NULL,
    pluralform           integer NOT NULL,
    activesubmission     integer,
    publishedsubmission  integer
);

-- ok. now we need to populate the new model with data from the old model.
-- fun for the whole family

INSERT INTO POSubmission
    (pomsgset, pluralform, potranslation, person, origin, datecreated,
    potranslationsighting)
    SELECT 
        pomsgset,
        pluralform,
        potranslation,
        person,
        origin,
        datefirstseen,
        id
    FROM POTranslationSighting;

-- we need to populate the POSelection table with a bunch of
-- msgset-pluralform pairs (nothing active or published). we will fill in
-- active / published details later

INSERT INTO POSelection
    (pomsgset, pluralform)
    SELECT DISTINCT
        pomsgset,
        pluralform
    FROM POTranslationSighting;

-- we should make sure we're ready to process lots of queries against
-- poselection and posubmission now

ANALYZE POSelection; -- No need to vacuum - no empty rows
ANALYZE POSubmission;

-- These are the indexes required for the next set of updates;

CREATE INDEX posubmission_potranslationsighting_idx ON
    POSubmission(potranslationsighting);

CREATE INDEX potranslationsighting_active_idx ON
    POTranslationSighting(active);

CREATE INDEX potranslationsighting_inlastrevision_idx ON
    POTranslationSighting(inlastrevision);

CREATE INDEX poselection_pomsgset_and_pluralform_idx ON
    POSelection(pomsgset, pluralform);

CREATE INDEX posubmission_pomsgset_and_pluralform_idx ON
    POSubmission(pomsgset, pluralform);

-- next, we must note which of these
-- selections is active, and which is published

UPDATE POSelection
    SET activesubmission=POSubmission.id
    FROM POTranslationSighting, POSubmission
    WHERE
        POTranslationSighting.active IS TRUE AND
        POTranslationSighting.id=POSubmission.potranslationsighting AND
        POSelection.pomsgset=POSubmission.pomsgset AND
        POSelection.pluralform=POSubmission.pluralform;

UPDATE POSelection
    SET publishedsubmission=POSubmission.id
    FROM POTranslationSighting, POSubmission
    WHERE
        POTranslationSighting.inlastrevision IS TRUE AND
        POTranslationSighting.id=POSubmission.potranslationsighting AND
        POSelection.pomsgset=POSubmission.pomsgset AND
        POSelection.pluralform=POSubmission.pluralform;

ANALYSE POSelection;


-- we need to remember better the state of the published pofile
ALTER TABLE POMsgSet ADD COLUMN publishedfuzzy boolean;
ALTER TABLE POMsgSet ADD COLUMN publishedcomplete boolean;

-- and distinguish the published status from the active status
ALTER TABLE POMsgSet RENAME COLUMN fuzzy TO isfuzzy;

-- in addition, per msgset, we need to cache a sense of whether or not
-- it is an update, or a new translation, because otherwise we cannot
-- calculate the statistics effectively

ALTER TABLE POMsgSet ADD COLUMN isupdated boolean;

-- we need to guess which messages were fuzzy and which were complete. this
-- is difficult, in fact impossible, so we will just assume that things that
-- were fuzzy are still fuzzy. This will be cleaned up the next time we do
-- an import, anyhow

UPDATE POMsgSet SET publishedfuzzy = isfuzzy,
                    publishedcomplete = iscomplete,
                    isupdated = FALSE;

-- in general we assume a new msgset is not published fuzzy
ALTER TABLE POMsgSet ALTER COLUMN publishedfuzzy SET NOT NULL;
ALTER TABLE POMsgSet ALTER COLUMN publishedfuzzy SET DEFAULT FALSE;

-- in general, any new pomsgset will not be complete
ALTER TABLE POMsgSet ALTER COLUMN publishedcomplete SET DEFAULT FALSE;
ALTER TABLE POMsgSet ALTER COLUMN publishedcomplete SET NOT NULL;

-- and a new one won't be updated in rosetta, either
ALTER TABLE POMsgSet ALTER COLUMN isupdated SET DEFAULT FALSE;
ALTER TABLE POMsgSet ALTER COLUMN isupdated SET NOT NULL;

ANALYSE POMsgSet;

-- Now we have inserted all our data, add the primary key constraints to
-- POSubmission and POSelection
ALTER TABLE posubmission ADD CONSTRAINT posubmission_pkey PRIMARY KEY (id);
ALTER TABLE poselection ADD CONSTRAINT poselection_pkey PRIMARY KEY (id);

-- and add some performance-enhancing indexes for rosetta

CREATE INDEX posubmission_potranslation_idx ON POSubmission(potranslation);
CREATE INDEX posubmission_person_idx ON POSubmission(person);
CREATE INDEX pomsgset_pofile_and_sequence_idx ON POMsgSet(pofile, sequence);

-- restructure the pomsgset indexes and keys
DROP INDEX pomsgset_potmsgset_key;
ALTER TABLE POMsgSet DROP CONSTRAINT pomsgset_pofile_key;
ALTER TABLE POMsgSet ADD CONSTRAINT pomsgset_potmsgset_key
    UNIQUE (potmsgset, pofile);

-- Rename uglynamed constraint
ALTER TABLE POMsgSet DROP CONSTRAINT "$3";
ALTER TABLE POMsgSet ADD CONSTRAINT pomsgset_pofile_fk
    FOREIGN KEY (pofile) REFERENCES POFile;

-- these indexes refer to activesubmission and publishedsubmission so we
-- want to create them after we've setup those fields.

-- performance: an index so we can quickly find the places a submission
-- is active and published

CREATE INDEX poselection_activesubmission_idx ON
    POSelection(activesubmission);

CREATE INDEX poselection_publishedsubmission_idx ON
    POSelection(publishedsubmission);

-- I think that these will be used for very fast joins backwards through
-- the POSelection table (i.e. given a Submission or Translation find out
-- where it is active, or published);

CREATE INDEX poselection_activesubmission_pomsgset_plural_idx ON
    POSelection(activesubmission, pomsgset, pluralform);

CREATE INDEX poselection_pubishedsubmission_pomsgset_plural_idx ON
    POSelection(publishedsubmission, pomsgset, pluralform);

-- now that the inserts are done, we can add the constraints. We didn't
-- want constraints active at first because we knew the data was good
-- coming from potranslationsighting

ALTER TABLE POSubmission ALTER COLUMN datecreated SET NOT NULL;

ALTER TABLE POSubmission ADD CONSTRAINT
    posubmission_valid_pluralform CHECK (pluralform >= 0);

ALTER TABLE POSubmission ADD CONSTRAINT
    posubmission_pomsgset_fk FOREIGN KEY
        (pomsgset) REFERENCES POMsgSet(id);

ALTER TABLE POSubmission ADD CONSTRAINT
    posubmission_potranslation_fk FOREIGN KEY
        (potranslation) REFERENCES POTranslation(id);

ALTER TABLE POSubmission ADD CONSTRAINT 
    posubmission_person_fk FOREIGN KEY (person)
       REFERENCES Person(id);

-- this UNIQUE constraint allows for poselection_real_active_fk and
-- poselection_real_published_fk

ALTER TABLE POSubmission ADD CONSTRAINT posubmission_can_be_selected
    UNIQUE (pomsgset, pluralform, id);

-- ensure, if there is an active submission, that it is for this same
-- msgset and plural form. We add this constraint now, because weve updated
-- the data
ALTER TABLE POSelection ADD CONSTRAINT
    poselection_real_active_fk
    FOREIGN KEY (pomsgset, pluralform, activesubmission)
    REFERENCES POSubmission(pomsgset, pluralform, id);

-- and similarly for the published submission
ALTER TABLE POSelection ADD CONSTRAINT
    poselection_real_published_fk
    FOREIGN KEY (pomsgset, pluralform, publishedsubmission)
    REFERENCES POSubmission(pomsgset, pluralform, id);

-- these constraints would normally have been added after table creation but
-- we move them here to speed up the update performance of the db

ALTER TABLE POSelection ADD CONSTRAINT
    poselection_pomsgset_fk FOREIGN KEY (pomsgset)
    REFERENCES POMsgSet(id);

ALTER TABLE POSelection ADD CONSTRAINT
    poselection_valid_pluralform CHECK (pluralform >= 0);

-- make sure it is only possible to have one selection for a given
-- msgset and pluralform

ALTER TABLE POSelection ADD CONSTRAINT
    poselection_uniqueness UNIQUE (pomsgset, pluralform);

ANALYSE POSelection;
ANALYSE POSubmission;

-- completeness is much trickier. we will start by saying everything was
-- published as complete as it is now. then we will find strings which
-- are complete now but which have a plural form without a published
-- submission.

-- find incomplete published msgsets
UPDATE POMsgSet SET publishedcomplete = FALSE
    FROM POSelection
    WHERE
        POMsgSet.iscomplete=TRUE AND
        POMsgSet.id=POSelection.pomsgset AND
        POSelection.activesubmission IS NOT NULL AND
        POSelection.publishedsubmission IS NULL;

-- let's try and identify updated msgsets

UPDATE POMsgSet SET isupdated=TRUE
    FROM
        POSelection
        INNER JOIN POSubmission AS ActiveSubmission ON
            POSelection.activesubmission=ActiveSubmission.id
        INNER JOIN POSubmission As PublishedSubmission ON
            POSelection.publishedsubmission=PublishedSubmission.id
    WHERE
        POMsgSet.sequence > 0 AND
        POMsgSet.isfuzzy=FALSE AND
        POMsgSet.iscomplete=TRUE AND
        POMsgSet.publishedfuzzy=FALSE AND
        POMsgSet.publishedcomplete=TRUE AND
        POSelection.pomsgset=POMsgSet.id AND
        ActiveSubmission.datecreated > PublishedSubmission.datecreated;

-- we are looking up POTMsgSet's by primemsgid for the translation
-- suggestions

CREATE INDEX potmsgset_primemsgid_idx ON
    POTMsgSet(primemsgid);

-- we also generally want to know both the template AND sequence

CREATE INDEX potmsgset_potemplate_and_sequence_idx ON
    POTMsgSet(potemplate, sequence);

ANALYSE POTMsgSet;

-- let's bang all the potemplate and pofile stats into shape

UPDATE POTemplate
    SET messagecount=(
        SELECT count(*)
        FROM
            POTMsgSet
        WHERE
            POTMsgSet.potemplate=POTemplate.id AND
            POTMsgSet.sequence>0);


UPDATE POFile
    SET currentcount = (
        SELECT count(*)
        FROM
            POMsgSet INNER JOIN POTMsgSet ON
                POMsgSet.potmsgset=POTMsgSet.id
        WHERE
            POMsgSet.pofile = POFile.id AND
            POMsgSet.sequence > 0 AND
            POMsgSet.publishedfuzzy = FALSE AND
            POMsgSet.publishedcomplete = TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0 );

UPDATE POFile
    SET updatescount = (
        SELECT count(*)
        FROM
            POMsgSet INNER JOIN POTMsgSet ON
                POMsgSet.potmsgset=POTMsgSet.id
        WHERE
            POMsgSet.pofile = POFile.id AND
            POMsgSet.sequence > 0 AND
            POMsgSet.isfuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE AND
            POMsgSet.publishedfuzzy = FALSE AND
            POMsgSet.publishedcomplete = TRUE AND
            POMsgSet.isupdated = TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0 );

UPDATE POFile SET rosettacount = (
    SELECT count(*)
    FROM
        POMsgSet INNER JOIN POTMsgSet ON
            POMsgSet.potmsgset=POTMsgSet.id
    WHERE
        POMsgSet.pofile = POFile.id AND
        POMsgSet.isfuzzy = FALSE AND
        POMsgSet.iscomplete = TRUE AND
      ( POMsgSet.sequence < 1 OR
        POMsgSet.publishedfuzzy = TRUE OR
        POMsgSet.publishedcomplete = FALSE ) AND
        POMsgSet.potmsgset = POTMsgSet.id AND
        POTMsgSet.sequence > 0 );

-- and now, the big cahunas. ok, maybe we'll just shunt it to one side
DROP INDEX posubmission_potranslationsighting_idx;
ALTER TABLE POSubmission DROP COLUMN potranslationsighting;
ALTER TABLE POTranslationSighting RENAME TO POTranslationSightingBackup;

-- let's recreate the POExport view using the new model.

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
        ON potmsgset.id = pomsgset.potmsgset
    LEFT OUTER JOIN poselection
        ON pomsgset.id = poselection.pomsgset
    LEFT OUTER JOIN posubmission
        ON posubmission.id = poselection.activesubmission
    LEFT OUTER JOIN potranslation
        ON potranslation.id = posubmission.potranslation
WHERE
    pomsgset.id IS NULL OR pomsgset.pofile = pofile.id;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 17, 0);
