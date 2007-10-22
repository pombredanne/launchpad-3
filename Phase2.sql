-- Migration script for "Phase 2" Translations database schema optimization.

BEGIN;

-- Merge POMsgSet into POSubmission as new class TranslationMessage

CREATE TABLE TranslationMessage(
	id serial,
	msgstr0 integer,
	msgstr1 integer,
	msgstr2 integer,
	msgstr3 integer,
	origin integer NOT NULL,
	datecreated timestamp without time zone
		DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
	person integer NOT NULL,
	validationstatus integer DEFAULT 0 NOT NULL,
	active boolean DEFAULT false NOT NULL,
	published boolean DEFAULT false NOT NULL,

	sequence integer NOT NULL,
	pofile integer NOT NULL,
	obsolete boolean NOT NULL,
	isfuzzy boolean NOT NULL,
	potmsgset integer NOT NULL,
	date_reviewed timestamp without time zone,
	reviewer integer,

	msgsetid integer,
	id0 integer,
	id1 integer,
	id2 integer,
	id3 integer,
	commenttext text,

	CONSTRAINT translationmessage__reviewer__date_reviewed__valid CHECK ((reviewer IS NULL) = (date_reviewed IS NULL))
);

ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__person__fk
	FOREIGN KEY (person) REFERENCES person(id);
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
	FOREIGN KEY (reviewer) REFERENCES person(id);
ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__pofile__fk
	FOREIGN KEY (pofile) REFERENCES pofile(id);
ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage__potmsgset__fk
	FOREIGN KEY (potmsgset) REFERENCES potmsgset(id);

CREATE UNIQUE INDEX translationmessage__potmsgset__pofile__active__key
	ON TranslationMessage(potmsgset, pofile) WHERE active;
CREATE UNIQUE INDEX translationmessage__potmsgset__pofile__published__key
	ON TranslationMessage(potmsgset, pofile) WHERE published;
CREATE INDEX translationmessage__person__idx ON TranslationMessage(person);
CREATE INDEX translationmessage__pofile__sequence__idx
	ON TranslationMessage(pofile, sequence);
CREATE INDEX translationmessage__reviewer__idx
	ON TranslationMessage(reviewer);
CREATE INDEX translationmessage__sequence__idx
	ON TranslationMessage(sequence);

CREATE INDEX translationmessage__msgstr0__idx ON TranslationMessage(msgstr0);
CREATE INDEX translationmessage__msgstr1__idx ON TranslationMessage(msgstr1);
CREATE INDEX translationmessage__msgstr2__idx ON TranslationMessage(msgstr2);
CREATE INDEX translationmessage__msgstr3__idx ON TranslationMessage(msgstr3);


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

-- Bundle POSubmissions that are both active and published.
INSERT INTO TranslationMessage(
	msgstr0, msgstr1, msgstr2, msgstr3, origin, datecreated, person,
	validationstatus, active, published, sequence, pofile, obsolete,
	isfuzzy, potmsgset, date_reviewed, reviewer,
	msgsetid, id0, id1, id2, id3, commenttext)
SELECT
	s0.potranslation AS msgstr0,
	s1.potranslation AS msgstr1,
	s2.potranslation AS msgstr2,
	s3.potranslation AS msgstr3,
	COALESCE(s0.origin, s1.origin, s2.origin, s3.origin) AS origin,
	COALESCE(s0.datecreated, s1.datecreated, s2.datecreated, s3.datecreated) AS datecreated,
	COALESCE(s0.person, s1.person, s2.person, s3.person) AS person,
	COALESCE(s0.validationstatus, 1) AS validationstatus,
	TRUE AS active,
	TRUE AS published,

	m.sequence AS sequence,
	m.pofile AS pofile,
	m.obsolete AS obsolete,
	m.isfuzzy AS isfuzzy,
	m.potmsgset AS potmsgset,
	m.date_reviewed AS date_reviewed,
	m.reviewer AS reviewer,

	m.id AS msgsetid,
	s0.id AS id0,
	s1.id AS id1,
	s2.id AS id2,
	s3.id AS id3,

	m.commenttext AS commenttext
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

-- Bundle POSubmissions that are active but not all published.
INSERT INTO TranslationMessage(
	msgstr0, msgstr1, msgstr2, msgstr3, origin, datecreated, person,
	validationstatus, active, published, sequence, pofile, obsolete,
	isfuzzy, potmsgset, date_reviewed, reviewer,
	msgsetid, id0, id1, id2, id3, commenttext)
SELECT
	s0.potranslation AS msgstr0,
	s1.potranslation AS msgstr1,
	s2.potranslation AS msgstr2,
	s3.potranslation AS msgstr3,
	COALESCE(s0.origin, s1.origin, s2.origin, s3.origin) AS origin,
	COALESCE(s0.datecreated, s1.datecreated, s2.datecreated, s3.datecreated) AS datecreated,
	COALESCE(s0.person, s1.person, s2.person, s3.person) AS person,
	COALESCE(s0.validationstatus, 1) AS validationstatus,
	TRUE AS active,
	FALSE AS published,

	m.sequence AS sequence,
	m.pofile AS pofile,
	m.obsolete AS obsolete,
	m.isfuzzy AS isfuzzy,
	m.potmsgset AS potmsgset,
	m.date_reviewed AS date_reviewed,
	m.reviewer AS reviewer,

	m.id AS msgsetid,
	s0.id AS id0,
	s1.id AS id1,
	s2.id AS id2,
	s3.id AS id3,

	m.commenttext AS commenttext
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

-- Bundle POSubmissions that are published but not all active.
INSERT INTO TranslationMessage(
	msgstr0, msgstr1, msgstr2, msgstr3, origin, datecreated, person,
	validationstatus, active, published, sequence, pofile, obsolete,
	isfuzzy, potmsgset, date_reviewed, reviewer,
	msgsetid, id0, id1, id2, id3, commenttext)
SELECT
	s0.potranslation AS msgstr0,
	s1.potranslation AS msgstr1,
	s2.potranslation AS msgstr2,
	s3.potranslation AS msgstr3,
	COALESCE(s0.origin, s1.origin, s2.origin, s3.origin) AS origin,
	COALESCE(s0.datecreated, s1.datecreated, s2.datecreated, s3.datecreated) AS datecreated,
	COALESCE(s0.person, s1.person, s2.person, s3.person) AS person,
	COALESCE(s0.validationstatus, 1) AS validationstatus,
	FALSE AS active,
	TRUE AS published,

	m.sequence AS sequence,
	m.pofile AS pofile,
	m.obsolete AS obsolete,
	m.isfuzzy AS isfuzzy,
	m.potmsgset AS potmsgset,
	m.date_reviewed AS date_reviewed,
	m.reviewer AS reviewer,

	m.id AS msgsetid,
	s0.id AS id0,
	s1.id AS id1,
	s2.id AS id2,
	s3.id AS id3,

	m.commenttext AS commenttext
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

-- Bundle POSubmissions that are not all published or active.
INSERT INTO TranslationMessage(
	msgstr0, msgstr1, msgstr2, msgstr3, origin, datecreated, person,
	validationstatus, active, published, sequence, pofile, obsolete,
	isfuzzy, potmsgset, date_reviewed, reviewer,
	msgsetid, id0, id1, id2, id3, commenttext)
SELECT
	s0.potranslation AS msgstr0,
	s1.potranslation AS msgstr1,
	s2.potranslation AS msgstr2,
	s3.potranslation AS msgstr3,
	COALESCE(s0.origin, s1.origin, s2.origin, s3.origin) AS origin,
	COALESCE(s0.datecreated, s1.datecreated, s2.datecreated, s3.datecreated) AS datecreated,
	COALESCE(s0.person, s1.person, s2.person, s3.person) AS person,
	COALESCE(s0.validationstatus, 1) AS validationstatus,
	FALSE AS active,
	FALSE AS published,

	m.sequence AS sequence,
	m.pofile AS pofile,
	m.obsolete AS obsolete,
	m.isfuzzy AS isfuzzy,
	m.potmsgset AS potmsgset,
	m.date_reviewed AS date_reviewed,
	m.reviewer AS reviewer,

	m.id AS msgsetid,
	s0.id AS id0,
	s1.id AS id1,
	s2.id AS id2,
	s3.id AS id3,

	m.commenttext AS commenttext
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


DROP TABLE POFileTranslator;

-- Redirect foreign-key constraints pointing to POMsgSet
ALTER TABLE POFile DROP CONSTRAINT pofile_last_touched_pomsgset_fkey;

DROP VIEW POExport;

DROP TABLE POSubmission;
DROP TABLE POMsgSet;

ALTER TABLE ONLY TranslationMessage
	ADD CONSTRAINT translationmessage_pkey PRIMARY KEY (id);

-- Restore foreign-key constraints previously pointing to POMsgSet
ALTER TABLE POFile ADD COLUMN last_touched_message integer;
ALTER TABLE POFile
	ADD CONSTRAINT pofile__last_touched_message__fkey FOREIGN KEY (last_touched_message) REFERENCES TranslationMessage(id);
UPDATE POFile
SET last_touched_message = Pos.id
FROM TranslationMessage Pos
WHERE last_touched_pomsgset = Pos.msgsetid;
ALTER TABLE POFile DROP COLUMN last_touched_pomsgset;

-- Merge POTemplateName into POTemplate

ALTER TABLE POTemplate ADD COLUMN name text;
ALTER TABLE POTemplate ADD COLUMN translationdomain text;

UPDATE POTemplate
SET name = ptn.name, translationdomain = ptn.translationdomain
FROM POTemplateName ptn
WHERE potemplatename = ptn.id;

ALTER TABLE POTemplate ALTER name SET NOT NULL;
ALTER TABLE POTemplate ALTER translationdomain SET NOT NULL;

DROP VIEW POTExport;

ALTER TABLE POTemplate DROP COLUMN potemplatename;
DROP TABLE POTemplateName;

ALTER TABLE POTemplate
	ADD CONSTRAINT potemplate_valid_name CHECK (valid_name(name));

-- Merge POMsgIDSighting into POTMsgSet
ALTER TABLE POTMsgSet RENAME primemsgid TO msgid;
ALTER TABLE POTMsgSet ADD COLUMN msgid_plural integer;

ALTER TABLE POTMsgSet
	ADD CONSTRAINT potmsgset__msgid_plural__fk FOREIGN KEY (msgid_plural) REFERENCES POMsgID(id);

UPDATE POTMsgSet
SET msgid_plural = sighting.pomsgid
FROM POMsgIDSighting sighting
WHERE sighting.potmsgset = POTMsgSet.id AND pluralform = 1;

DROP TABLE POMsgIDSighting;

-- Restore POExport view
CREATE VIEW POExport(
	id,
	name,
	translationdomain,
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
	posequence,
	obsolete,
	isfuzzy,
	pocommenttext,
	translation0,
	translation1,
	translation2,
	translation3,
	activesubmission,
	context,
	msgid,
	msgid_plural
	) AS
SELECT
	COALESCE(potmsgset.id::text, 'X'::text) || '.'::text || COALESCE(translationmessage.id::text, 'X'::text) AS id,
	potemplate.name,
	potemplate.translationdomain,
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
	translationmessage."sequence" AS posequence,
	translationmessage.obsolete,
	translationmessage.isfuzzy,
	translationmessage.commenttext AS pocommenttext,
	potranslation0.translation AS translation0,
	potranslation1.translation AS translation1,
	potranslation2.translation AS translation2,
	potranslation3.translation AS translation3,
	translationmessage.id AS activesubmission,
	potmsgset.context,
	msgid.msgid,
	msgid_plural.msgid AS msgid_plural
FROM potmsgset
JOIN potemplate ON potemplate.id = potmsgset.potemplate
JOIN pofile ON potemplate.id = pofile.potemplate
LEFT JOIN TranslationMessage ON
	potmsgset.id = translationmessage.potmsgset AND
	translationmessage.pofile = pofile.id AND translationmessage.active
LEFT JOIN pomsgid AS msgid ON msgid.id = potmsgset.msgid
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
	translationdomain,
	potemplate,
	productseries,
	sourcepackagename,
	distrorelease,
	header,
	languagepack,
	potmsgset,
	sequence,
	commenttext,
	sourcecomment,
	flagscomment,
	filereferences,
	context,
	msgid,
	msgid_plural
	) AS
SELECT
	COALESCE(potmsgset.id::text, 'X'::text) AS id,
	potemplate.name,
	potemplate.translationdomain,
	potemplate.id AS potemplate,
	potemplate.productseries,
	potemplate.sourcepackagename,
	potemplate.distrorelease,
	potemplate."header",
	potemplate.languagepack,
	potmsgset.id AS potmsgset,
	potmsgset."sequence",
	potmsgset.commenttext,
	potmsgset.sourcecomment,
	potmsgset.flagscomment,
	potmsgset.filereferences,
	potmsgset.context,
	msgid.msgid,
	msgid_plural.msgid AS msgid_plural
FROM POTMsgSet
JOIN potemplate ON potemplate.id = potmsgset.potemplate
LEFT JOIN POMsgID AS msgid ON POTMsgSet.msgid = msgid.id
LEFT JOIN POMsgID AS msgid_plural ON POTMsgSet.msgid_plural = msgid_plural.id;

-- Clean up columns that were only for use during migration.
ALTER TABLE TranslationMessage DROP COLUMN msgsetid;
ALTER TABLE TranslationMessage DROP COLUMN id0;
ALTER TABLE TranslationMessage DROP COLUMN id1;
ALTER TABLE TranslationMessage DROP COLUMN id2;
ALTER TABLE TranslationMessage DROP COLUMN id3;

-- Re-create POFileTranslator (replacing latest_posubmission)
CREATE TABLE POFileTranslator (
	id integer NOT NULL,
	person integer NOT NULL,
	pofile integer NOT NULL,
	latest_message integer NOT NULL,
	date_last_touched timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL);

-- TODO: Re-populate POFileTranslator
-- TODO: Rewrite triggers that keep POFileTranslator updated

ROLLBACK;

