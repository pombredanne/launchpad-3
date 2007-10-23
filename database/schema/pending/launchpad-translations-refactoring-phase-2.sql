-- Migration script for "Phase 2" Translations database schema optimization.

SET client_min_messages=ERROR;

BEGIN;

-- Merge POMsgSet into POSubmission as new class TranslationMessage

-- Columns are grouped by data size, with variable-length data coming at the
-- end.  This has been shown to improve performance quite radially in some
-- cases.

SELECT 'Creating TranslationMessage', statement_timestamp();	-- DEBUG

CREATE TABLE TranslationMessage(
	id serial,
	msgstr0 integer,
	msgstr1 integer,
	msgstr2 integer,
	msgstr3 integer,
	pofile integer NOT NULL,
	potmsgset integer NOT NULL,
	origin integer NOT NULL,
	submitter integer NOT NULL,
	reviewer integer,
	validationstatus integer DEFAULT 0 NOT NULL,
	is_current boolean DEFAULT false NOT NULL,
	is_imported boolean DEFAULT false NOT NULL,
	was_in_last_import boolean NOT NULL,
	was_obsolete_in_last_import boolean NOT NULL,
	is_fuzzy boolean NOT NULL,
	date_created timestamp without time zone
		DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
	date_reviewed timestamp without time zone, 
	comment_text text,

	-- For migration purposes: references to objects that constitute this
	-- TranslationMessage.  Will be dropped later on.
	msgsetid integer,
	id0 integer,
	id1 integer,
	id2 integer,
	id3 integer
);


-- Create TranslationMessages based each on 1 POMsgSet and up to 4 associated
-- POSubmissions (for the up to 4 plural forms that we support).
-- How do we choose which POSubmissions to bundle into one TranslationMessage?
--
-- 1. All active POSubmissions for a POMsgSet form one TranslationMessage.
-- 2. All published POSubmissions for a message set are likewise bundled.
-- 3. We bundle any combination of up to 4 POSubmissions that have the same
--    POMsgSet, person, and datecreated (and different pluralforms).
--
-- Active or published POSubmissions may be represented in more than one
-- TranslationMessage: once in the "bundle" they were submitted with and once
-- as part of the active/published TranslationMessage.
--
-- A TranslationMessage is thus active/published if the POSubmissions it
-- combines are all active/published.
--
-- All this must be done with some nasty corner cases in mind:
--
-- * Submissions for any pluralforms, including pluralform 0, may be missing.
--
-- * Say for a given POMsgSet we have POSubmissions X in pluralform 0, both
--   active and published; Y in pluralform 1, active but not published; and Z
--   also in pluralform 1 but published and not active.  Those should form at
--   least an active TranslationMessage with X and Y, and a published one that
--   contains X and Z.
--
-- * If in the same situation we have only POSubmissions X and Y, X and Z
--   should form an active TranslationMessage and there should still be a
--   separate published one with only X.
--
-- We deal with the active/published problems in steps: we do bundling of
-- active, published POSubmissions in one query, active but non-published ones
-- in another and so on.

SELECT 'Migrating active, published submissions', statement_timestamp();	-- DEBUG

-- Bundle POSubmissions that are both active and published.
INSERT INTO TranslationMessage(
	msgstr0, msgstr1, msgstr2, msgstr3, pofile, potmsgset, origin,
	submitter, reviewer, validationstatus, is_current, is_imported,
	was_in_last_import, was_obsolete_in_last_import, is_fuzzy,
	date_created, date_reviewed, comment_text,
	msgsetid, id0, id1, id2, id3)
SELECT
	s0.potranslation AS msgstr0,
	s1.potranslation AS msgstr1,
	s2.potranslation AS msgstr2,
	s3.potranslation AS msgstr3,
	m.pofile AS pofile,
	m.potmsgset AS potmsgset,
	COALESCE(s0.origin, s1.origin, s2.origin, s3.origin) AS origin,
	COALESCE(s0.person, s1.person, s2.person, s3.person) AS submitter,
	m.reviewer AS reviewer,
	COALESCE(s0.validationstatus, 1) AS validationstatus,
	TRUE AS is_current,
	TRUE AS is_imported,
	(m.sequence > 0) AS was_in_last_import,
	m.obsolete AS was_obsolete_in_last_import,
	m.isfuzzy AS is_fuzzy,
	COALESCE(s0.datecreated, s1.datecreated, s2.datecreated, s3.datecreated)
		AS date_created,
	m.date_reviewed AS date_reviewed,
	m.commenttext AS comment_text,

	m.id AS msgsetid,
	s0.id AS id0,
	s1.id AS id1,
	s2.id AS id2,
	s3.id AS id3
FROM POMsgSet m
LEFT OUTER JOIN POSubmission AS s0 ON
	s0.pomsgset = m.id AND
	s0.pluralform = 0
LEFT OUTER JOIN POSubmission AS s1 ON
	s1.pomsgset = m.id AND
	s1.pluralform = 1
LEFT OUTER JOIN POSubmission AS s2 ON
	s2.pomsgset = m.id AND
	s2.pluralform = 2
LEFT OUTER JOIN POSubmission AS s3 ON
	s3.pomsgset = m.id AND
	s3.pluralform = 3
WHERE
	(s0.id IS NOT NULL OR
	 s1.id IS NOT NULL OR
	 s2.id IS NOT NULL OR
	 s3.id IS NOT NULL) AND
	s0.active IS NOT FALSE AND
	s1.active IS NOT FALSE AND
	s2.active IS NOT FALSE AND
	s3.active IS NOT FALSE AND
	s0.published IS NOT FALSE AND
	s1.published IS NOT FALSE AND
	s2.published IS NOT FALSE AND
	s3.published IS NOT FALSE
;

SELECT 'Migrating active, non-published submissions', statement_timestamp();	-- DEBUG

-- Bundle POSubmissions that are active but not all published.
INSERT INTO TranslationMessage(
	msgstr0, msgstr1, msgstr2, msgstr3, pofile, potmsgset, origin,
	submitter, reviewer, validationstatus, is_current, is_imported,
	was_in_last_import, was_obsolete_in_last_import, is_fuzzy,
	date_created, date_reviewed, comment_text,
	msgsetid, id0, id1, id2, id3)
SELECT
	s0.potranslation AS msgstr0,
	s1.potranslation AS msgstr1,
	s2.potranslation AS msgstr2,
	s3.potranslation AS msgstr3,
	m.pofile AS pofile,
	m.potmsgset AS potmsgset,
	COALESCE(s0.origin, s1.origin, s2.origin, s3.origin) AS origin,
	COALESCE(s0.person, s1.person, s2.person, s3.person) AS submitter,
	m.reviewer AS reviewer,
	COALESCE(s0.validationstatus, 1) AS validationstatus,
	TRUE AS is_current,
	FALSE AS is_imported,
	FALSE AS was_in_last_import,
	m.obsolete AS was_obsolete_in_last_import,
	m.isfuzzy AS is_fuzzy,
	COALESCE(s0.datecreated, s1.datecreated, s2.datecreated, s3.datecreated)
		AS date_created,
	m.date_reviewed AS date_reviewed,
	m.commenttext AS comment_text,

	m.id AS msgsetid,
	s0.id AS id0,
	s1.id AS id1,
	s2.id AS id2,
	s3.id AS id3
FROM POMsgSet m
LEFT OUTER JOIN POSubmission AS s0 ON
	s0.pomsgset = m.id AND
	s0.pluralform = 0 AND
	s0.active
LEFT OUTER JOIN POSubmission AS s1 ON
	s1.pomsgset = m.id AND
	s1.pluralform = 1 AND
	s1.active
LEFT OUTER JOIN POSubmission AS s2 ON
	s2.pomsgset = m.id AND
	s2.pluralform = 2 AND
	s2.active
LEFT OUTER JOIN POSubmission AS s3 ON
	s3.pomsgset = m.id AND
	s3.pluralform = 3 AND
	s3.active
WHERE
	-- At least one "published" must be an actual FALSE (not just NULL).
	NOT s0.published OR
	NOT s1.published OR
	NOT s2.published OR
	NOT s3.published
;

SELECT 'Migrating non-active, published submissions', statement_timestamp();	-- DEBUG

-- Bundle POSubmissions that are published but not all active.
INSERT INTO TranslationMessage(
	msgstr0, msgstr1, msgstr2, msgstr3, pofile, potmsgset, origin,
	submitter, reviewer, validationstatus, is_current, is_imported,
	was_in_last_import, was_obsolete_in_last_import, is_fuzzy,
	date_created, date_reviewed, comment_text,
	msgsetid, id0, id1, id2, id3)
SELECT
	s0.potranslation AS msgstr0,
	s1.potranslation AS msgstr1,
	s2.potranslation AS msgstr2,
	s3.potranslation AS msgstr3,
	m.pofile AS pofile,
	m.potmsgset AS potmsgset,
	COALESCE(s0.origin, s1.origin, s2.origin, s3.origin) AS origin,
	COALESCE(s0.person, s1.person, s2.person, s3.person) AS submitter,
	m.reviewer AS reviewer,
	COALESCE(s0.validationstatus, 1) AS validationstatus,
	FALSE AS is_current,
	TRUE AS is_imported,

	(m.sequence > 0) AS was_in_last_import,
	m.obsolete AS was_obsolete_in_last_import,
	m.isfuzzy AS is_fuzzy,
	COALESCE(s0.datecreated, s1.datecreated, s2.datecreated, s3.datecreated)
		AS date_created,
	m.date_reviewed AS date_reviewed,
	m.commenttext AS comment_text,

	m.id AS msgsetid,
	s0.id AS id0,
	s1.id AS id1,
	s2.id AS id2,
	s3.id AS id3
FROM POMsgSet m
LEFT OUTER JOIN POSubmission AS s0 ON
	s0.pomsgset = m.id AND
	s0.pluralform = 0 AND
	s0.published
LEFT OUTER JOIN POSubmission AS s1 ON
	s1.pomsgset = m.id AND
	s1.pluralform = 1 AND
	s1.published
LEFT OUTER JOIN POSubmission AS s2 ON
	s2.pomsgset = m.id AND
	s2.pluralform = 2 AND
	s2.published
LEFT OUTER JOIN POSubmission AS s3 ON
	s3.pomsgset = m.id AND
	s3.pluralform = 3 AND
	s3.published
WHERE
	-- At least one "active" must be FALSE (not just NULL).
	NOT s0.active OR NOT s1.active OR NOT s2.active OR NOT s3.active
;

SELECT 'Migrating non-active, non-published submissions', statement_timestamp();	-- DEBUG

-- Bundle POSubmissions that are not all published or active (but are all by
-- the same person and created at the same time).
INSERT INTO TranslationMessage(
	msgstr0, msgstr1, msgstr2, msgstr3, pofile, potmsgset, origin,
	submitter, reviewer, validationstatus, is_current, is_imported,
	was_in_last_import, was_obsolete_in_last_import, is_fuzzy,
	date_created, date_reviewed, comment_text,
	msgsetid, id0, id1, id2, id3)
SELECT
	s0.potranslation AS msgstr0,
	s1.potranslation AS msgstr1,
	s2.potranslation AS msgstr2,
	s3.potranslation AS msgstr3,
	m.pofile AS pofile,
	m.potmsgset AS potmsgset,
	COALESCE(s0.origin, s1.origin, s2.origin, s3.origin) AS origin,
	COALESCE(s0.person, s1.person, s2.person, s3.person) AS submitter,
	m.reviewer AS reviewer,
	COALESCE(s0.validationstatus, 1) AS validationstatus,
	FALSE AS is_current,
	FALSE AS is_imported,
	FALSE AS was_in_last_import,
	m.obsolete AS was_obsolete_in_last_import,
	m.isfuzzy AS is_fuzzy,
	COALESCE(s0.datecreated, s1.datecreated, s2.datecreated, s3.datecreated)
		AS date_created,
	m.date_reviewed AS date_reviewed,
	m.commenttext AS comment_text,

	m.id AS msgsetid,
	s0.id AS id0,
	s1.id AS id1,
	s2.id AS id2,
	s3.id AS id3
FROM POMsgSet m
LEFT OUTER JOIN POSubmission AS s0 ON
	s0.pomsgset = m.id AND
	s0.pluralform = 0
LEFT OUTER JOIN POSubmission AS s1 ON
	s1.pomsgset = m.id AND
	s1.pluralform = 1 AND
	(s0.id IS NULL OR
	 (s1.person = s0.person AND
	  s1.datecreated = s0.datecreated))
LEFT OUTER JOIN POSubmission AS s2 ON
	s2.pomsgset = m.id AND
	s2.pluralform = 2 AND
	((s0.id IS NULL AND s1.id IS NULL) OR
	 (s2.person = COALESCE(s0.person, s1.person) AND
	  s2.datecreated = COALESCE(s0.datecreated, s1.datecreated)))
LEFT OUTER JOIN POSubmission AS s3 ON
	s3.pomsgset = m.id AND
	s3.pluralform = 3 AND
	((s0.id IS NULL AND s1.id IS NULL AND s2.id IS NULL) OR
	 (s3.person = COALESCE(s0.person, s1.person, s2.person) AND
	  s3.datecreated = COALESCE(s0.datecreated, s1.datecreated, s2.datecreated)))
WHERE
	(NOT s0.active OR NOT s1.active OR NOT s2.active OR NOT s3.active) AND
	(NOT s0.published OR
	 NOT s1.published OR
	 NOT s2.published OR
	 NOT s3.published)
;

SELECT 'Patching up ValidationStatus', statement_timestamp();	-- DEBUG

-- Update validationstatus: if any of the POSubmissions that are bundled needs
-- validation, validationstatus should be 0 (UNKNOWN).  Otherwise, if any has
-- an error, it should be 2 (UNKNOWNERROR).  Only if neither is the case can it
-- be left at whatever the pluralform-0 POSubmission had for its status.
UPDATE TranslationMessage
SET validationstatus = 2
FROM POSubmission Pos
WHERE
	Pos.pluralform > 0 AND
	(Pos.id = id1 OR Pos.id = id2 OR Pos.id = id3) AND
	Pos.validationstatus = 2;
UPDATE TranslationMessage
SET validationstatus = 0
FROM POSubmission Pos
WHERE
	Pos.pluralform > 0 AND
	(Pos.id = id1 OR Pos.id = id2 OR Pos.id = id3) AND
	Pos.validationstatus = 0;


SELECT 'Indexing TranslationMessage table', statement_timestamp();	-- DEBUG

CREATE UNIQUE INDEX translationmessage__potmsgset__pofile__is_current__key
	ON TranslationMessage(potmsgset, pofile) WHERE is_current;
CREATE UNIQUE INDEX translationmessage__potmsgset__pofile__is_imported__key
	ON TranslationMessage(potmsgset, pofile) WHERE is_imported;
CREATE INDEX translationmessage__submitter__idx
	ON TranslationMessage(submitter);
CREATE INDEX translationmessage__reviewer__idx
	ON TranslationMessage(reviewer);
-- TODO: Do we actually need indexes on was_in_last_import?
CREATE INDEX translationmessage__pofile__was_in_last_import__idx
	ON TranslationMessage(pofile, was_in_last_import);
CREATE INDEX translationmessage__was_in_last_import__idx
	ON TranslationMessage(was_in_last_import);

CREATE INDEX translationmessage__msgstr0__idx ON TranslationMessage(msgstr0);
CREATE INDEX translationmessage__msgstr1__idx ON TranslationMessage(msgstr1);
CREATE INDEX translationmessage__msgstr2__idx ON TranslationMessage(msgstr2);
CREATE INDEX translationmessage__msgstr3__idx ON TranslationMessage(msgstr3);


SELECT 'Adding constraints to TranslationMessage table', statement_timestamp();	-- DEBUG

ALTER TABLE TranslationMessage
	ADD CONSTRAINT translationmessage_pkey PRIMARY KEY (id);

ALTER TABLE TranslationMessage
	ADD CONSTRAINT translationmessage__reviewer__date_reviewed__valid
	CHECK ((reviewer IS NULL) = (date_reviewed IS NULL));
ALTER TABLE TranslationMessage
	ADD CONSTRAINT translationmessage__was_in_last_import__is_imported__valid
	CHECK (is_imported OR NOT was_in_last_import);
ALTER TABLE TranslationMessage
	ADD CONSTRAINT translationmessage__nonempty__valid
	CHECK (COALESCE(msgstr0, msgstr1, msgstr2, msgstr3) IS NOT NULL);
ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__submitter__fk
	FOREIGN KEY (submitter) REFERENCES Person(id);
ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__msgstr0__fk
	FOREIGN KEY (msgstr0) REFERENCES POTranslation(id);
ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__msgstr1__fk
	FOREIGN KEY (msgstr1) REFERENCES POTranslation(id);
ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__msgstr2__fk
	FOREIGN KEY (msgstr2) REFERENCES POTranslation(id);
ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__msgstr3__fk
	FOREIGN KEY (msgstr3) REFERENCES POTranslation(id);
ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__reviewer__fk
	FOREIGN KEY (reviewer) REFERENCES Person(id);
ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__pofile__fk
	FOREIGN KEY (pofile) REFERENCES pofile(id);
ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__potmsgset__fk
	FOREIGN KEY (potmsgset) REFERENCES potmsgset(id);


-- Redirect foreign-key constraints pointing to POMsgSet
ALTER TABLE POFile DROP CONSTRAINT pofile_last_touched_pomsgset_fkey;

DROP VIEW POExport;
DROP TABLE POFileTranslator;

DROP TABLE POSubmission;
DROP TABLE POMsgSet;


SELECT 'Retiring POFile.last_touched_pomsgset', statement_timestamp();	-- DEBUG

-- POFile.last_touched_pomsgset is no longer needed; instead POFile holds the
-- person who last modified a TranslationMessage in the POFile and the date of
-- the change.  There was already a column for the last translator, but it was
-- not maintained.
ALTER TABLE POFile ADD COLUMN date_created timestamp without time zone;

UPDATE POFile
SET
	date_created = TranslationMessage.date_created,
	lasttranslator = TranslationMessage.submitter
FROM TranslationMessage
WHERE TranslationMessage.id = POFile.last_touched_pomsgset;

ALTER TABLE POFile DROP COLUMN last_touched_pomsgset;


SELECT 'Retiring POTemplateName', statement_timestamp();	-- DEBUG

-- Merge POTemplateName into POTemplate
ALTER TABLE POTemplate ADD COLUMN name text;
ALTER TABLE POTemplate ADD COLUMN translation_domain text;

UPDATE POTemplate
SET name = ptn.name, translation_domain = ptn.translationdomain
FROM POTemplateName ptn
WHERE potemplatename = ptn.id;

ALTER TABLE POTemplate ALTER name SET NOT NULL;
ALTER TABLE POTemplate ALTER translation_domain SET NOT NULL;

DROP VIEW POTExport;

ALTER TABLE POTemplate DROP COLUMN potemplatename;
DROP TABLE POTemplateName;

ALTER TABLE POTemplate
	ADD CONSTRAINT potemplate_valid_name CHECK (valid_name(name));


SELECT 'Retiring POMsgIDSighting', statement_timestamp();	-- DEBUG

-- Merge POMsgIDSighting into POTMsgSet
ALTER TABLE POTMsgSet RENAME primemsgid TO msgid_singular;
ALTER TABLE POTMsgSet ADD COLUMN msgid_plural integer;
ALTER TABLE POTMsgSet
	ADD CONSTRAINT potmsgset__msgid_plural__fk
	FOREIGN KEY (msgid_plural) REFERENCES POMsgID(id);

UPDATE POTMsgSet
SET msgid_plural = sighting.pomsgid
FROM POMsgIDSighting sighting
WHERE sighting.potmsgset = POTMsgSet.id AND pluralform = 1;

DROP TABLE POMsgIDSighting;

SELECT 'Restoring export views', statement_timestamp();	-- DEBUG

-- Restore POExport view
CREATE VIEW POExport(
	id,
	name,
	translation_domain,
	potemplate,
	productseries,
	sourcepackagename,
	distrorelease,
	potheader,
	languagepack,
	pofile,
	language,
	variant,
	potopcomment,
	poheader,
	pofuzzyheader,
	potmsgset,
	potsequence,
	potcommenttext,
	sourcecomment,
	flagscomment,
	filereferences,
	was_in_last_import,
	was_obsolete_in_last_import,
	is_fuzzy,
	pocommenttext,
	translation0,
	translation1,
	translation2,
	translation3,
	current_translation,
	context,
	msgid_singular,
	msgid_plural
	) AS
SELECT
	COALESCE(potmsgset.id::text, 'X'::text) || '.'::text || COALESCE(translationmessage.id::text, 'X'::text) AS id,
	potemplate.name,
	potemplate.translation_domain,
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
	translationmessage.was_in_last_import AS was_in_last_import,
	translationmessage.was_obsolete_in_last_import,
	translationmessage.is_fuzzy,
	translationmessage.comment_text AS pocommenttext,
	potranslation0.translation AS translation0,
	potranslation1.translation AS translation1,
	potranslation2.translation AS translation2,
	potranslation3.translation AS translation3,
	translationmessage.id AS current_translation,
	potmsgset.context,
	msgid_singular.msgid AS msgid_singular,
	msgid_plural.msgid AS msgid_plural
FROM potmsgset
JOIN potemplate ON potemplate.id = potmsgset.potemplate
JOIN pofile ON potemplate.id = pofile.potemplate
LEFT JOIN TranslationMessage ON
	potmsgset.id = translationmessage.potmsgset AND
	translationmessage.pofile = pofile.id AND
	translationmessage.is_current
LEFT JOIN pomsgid AS msgid_singular ON msgid_singular.id = potmsgset.msgid_singular
LEFT JOIN pomsgid AS msgid_plural ON msgid_plural.id = potmsgset.msgid_plural
LEFT JOIN potranslation AS potranslation0 ON
	potranslation0.id = translationmessage.msgstr0
LEFT JOIN potranslation AS potranslation1 ON
	potranslation0.id = translationmessage.msgstr1
LEFT JOIN potranslation AS potranslation2 ON
	potranslation0.id = translationmessage.msgstr2
LEFT JOIN potranslation AS potranslation3 ON
	potranslation0.id = translationmessage.msgstr3
;

CREATE VIEW POTExport(
	id,
	name,
	translation_domain,
	potemplate,
	productseries,
	sourcepackagename,
	distrorelease,
	header,
	languagepack,
	potmsgset,
	sequence,
	comment_text,
	source_comment,
	flags_comment,
	file_references,
	context,
	msgid_singular,
	msgid_plural
	) AS
SELECT
	COALESCE(potmsgset.id::text, 'X'::text) AS id,
	potemplate.name,
	potemplate.translation_domain,
	potemplate.id AS potemplate,
	potemplate.productseries,
	potemplate.sourcepackagename,
	potemplate.distrorelease,
	potemplate."header",
	potemplate.languagepack,
	potmsgset.id AS potmsgset,
	potmsgset."sequence",
	potmsgset.commenttext AS comment_text,
	potmsgset.sourcecomment AS source_comment,
	potmsgset.flagscomment AS flags_comment,
	potmsgset.filereferences AS file_references,
	potmsgset.context,
	msgid_singular.msgid AS msgid_singular,
	msgid_plural.msgid AS msgid_plural
FROM POTMsgSet
JOIN potemplate ON potemplate.id = potmsgset.potemplate
LEFT JOIN POMsgID AS msgid_singular ON POTMsgSet.msgid_singular = msgid_singular.id
LEFT JOIN POMsgID AS msgid_plural ON POTMsgSet.msgid_plural = msgid_plural.id;


SELECT 'Cleaning up TranslationMessage temp columns', statement_timestamp();	-- DEBUG

-- Clean up columns that were only for use during migration.
ALTER TABLE TranslationMessage DROP COLUMN msgsetid;
ALTER TABLE TranslationMessage DROP COLUMN id0;
ALTER TABLE TranslationMessage DROP COLUMN id1;
ALTER TABLE TranslationMessage DROP COLUMN id2;
ALTER TABLE TranslationMessage DROP COLUMN id3;


SELECT 'Re-creating POFileTranslator', statement_timestamp();	-- DEBUG

-- Re-create POFileTranslator (replacing latest_posubmission)
CREATE TABLE POFileTranslator (
	id serial,
	person integer NOT NULL,
	pofile integer NOT NULL,
	latest_message integer NOT NULL,
	date_last_touched timestamp without time zone
		DEFAULT timezone('UTC'::text, now()) NOT NULL);

ALTER TABLE POFileTranslator
	ADD CONSTRAINT pofiletranslator_pkey PRIMARY KEY (id);

-- Re-populate POFileTranslator
INSERT INTO POFileTranslator (
    person, pofile, latest_message, date_last_touched
    )
SELECT DISTINCT ON (submitter, pofile) submitter, pofile, id, date_created
FROM TranslationMessage
ORDER BY submitter, pofile, date_created DESC, id DESC;

ALTER TABLE POFileTranslator
	ADD CONSTRAINT pofiletranslator__latest_message__fk
	FOREIGN KEY (latest_message) REFERENCES TranslationMessage(id)
	DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE POFileTranslator
	ADD CONSTRAINT pofiletranslator__person__fk
	FOREIGN KEY (person) REFERENCES Person(id);
ALTER TABLE POFileTranslator
	ADD CONSTRAINT pofiletranslator__pofile__fk
	FOREIGN KEY (pofile) REFERENCES POFile(id);
CREATE INDEX pofiletranslator__date_last_touched__idx
	ON POFileTranslator(date_last_touched);
ALTER TABLE POFileTranslator
	ADD CONSTRAINT pofiletranslator__person__pofile__key
	UNIQUE (person, pofile);
ALTER TABLE POFileTranslator CLUSTER ON pofiletranslator__person__pofile__key;

DROP FUNCTION IF EXISTS mv_pofiletranslator_posubmission();
DROP FUNCTION IF EXISTS mv_pofiletranslator_pomsgset();

CREATE OR REPLACE FUNCTION mv_pofiletranslator_translationmessage()
	RETURNS TRIGGER AS $$
DECLARE
    v_pofile INTEGER;
    v_trash_old BOOLEAN;
BEGIN
    -- If we are deleting a row, we need to remove the existing
    -- POFileTranslator row and reinsert the historical data if it exists.
    -- We also treat UPDATEs that change the key (submitter, pofile) the same
    -- as deletes. UPDATEs that don't change these columns are treated like
    -- INSERTs below.
    IF TG_OP = 'INSERT' THEN
        v_trash_old := FALSE;
    ELSIF TG_OP = 'DELETE' THEN
        v_trash_old := TRUE;
    ELSE -- UPDATE
        v_trash_old = (
            OLD.submitter != NEW.submitter OR OLD.pofile != NEW.pofile
            );
    END IF;

    IF v_trash_old THEN

        -- Delete the old record.
        DELETE FROM POFileTranslator
        WHERE POFileTranslator.latest_message = OLD.latest_message;

        -- Insert a past record if there is one.
        INSERT INTO POFileTranslator (
            person, pofile, latest_message, date_last_touched
            )
        SELECT DISTINCT ON (submitter, pofile)
            submitter, pofile, id, date_created
        FROM TranslationMessage
        WHERE pofile = OLD.pofile AND person = OLD.submitter
        ORDER BY person, pofile, date_created DESC, id DESC;

        -- No NEW with DELETE, so we can short circuit and leave.
        IF TG_OP = 'DELETE' THEN
            RETURN NULL; -- Ignored because this is an AFTER trigger
        END IF;
    END IF;

    -- Standard 'upsert' loop to avoid race conditions.
    LOOP
        UPDATE POFileTranslator
        SET
            date_last_touched = CURRENT_TIMESTAMP AT TIME ZONE 'UTC',
            latest_message = NEW.id
        WHERE person = NEW.submitter AND pofile = NEW.pofile;
        IF found THEN
            RETURN NULL; -- Return value ignored as this is an AFTER trigger
        END IF;

        BEGIN
            INSERT INTO POFileTranslator (person, pofile, latest_message)
            VALUES (NEW.submitter, NEW.pofile, NEW.id);
            RETURN NULL; -- Return value ignored as this is an AFTER trigger
        EXCEPTION WHEN unique_violation THEN
            -- do nothing
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mv_pofiletranslator_translationmessage() IS
    'Trigger maintaining the POFileTranslator table';

CREATE TRIGGER mv_pofiletranslator_translationmessage
	BEFORE INSERT OR DELETE OR UPDATE ON TranslationMessage
	FOR EACH ROW
	EXECUTE PROCEDURE mv_pofiletranslator_translationmessage();

SELECT 'Completing', statement_timestamp();	-- DEBUG

ROLLBACK;

