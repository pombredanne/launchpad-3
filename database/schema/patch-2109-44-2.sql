SET client_min_messages=ERROR;

-- This is half of a two part patch. The second half is patch-2109-48-0.sql,
-- This is the half we will attempt to apply to production before
-- the next rollout (after changing the CREATE INDEX statements to
-- CREATE INDEX CONCURRENTLY). This half of the patch cleans up indexes
-- that should no longer be needed after the rollout.


-- A POTemplate can have only one row with a certain sequence number.
CREATE UNIQUE INDEX translationtemplateitem__potemplate__sequence__key
ON translationtemplateitem (potemplate, sequence) WHERE sequence > 0;

-- Indexes used to match global suggestions, i.e. find related POTMsgSets
-- by context, msgid_singular and msgid_plural.
CREATE INDEX potmsgset__context__msgid_singular__msgid_plural__idx
ON potmsgset(context, msgid_singular, msgid_plural)
WHERE ((context IS NOT NULL) AND (msgid_plural IS NOT NULL));

CREATE INDEX potmsgset__context__msgid_singular__no_msgid_plural__idx
ON potmsgset(context, msgid_singular)
WHERE ((context IS NOT NULL) AND (msgid_plural IS NULL));

CREATE INDEX potmsgset__no_context__msgid_singular__msgid_plural__idx
ON potmsgset (msgid_singular, msgid_plural)
WHERE ((context IS NULL) AND (msgid_plural IS NOT NULL));

CREATE INDEX potmsgset__no_context__msgid_singular__no_msgid_plural__idx
ON potmsgset (msgid_singular)
WHERE ((context IS NULL) AND (msgid_plural IS NULL));

-- Help get all TTI rows for potemplate = X ordered by sequence.
CREATE INDEX translationtemplateitem__potemplate__sequence__idx
ON translationtemplateitem (potemplate, sequence);

-- A POFile link is gone from translationmessage, replaced with
-- language/variant combination, where variant can be NULL.
CREATE INDEX translationmessage__language__variant__submitter__idx
ON translationmessage (language, variant, submitter)
WHERE (variant IS NOT NULL);
CREATE INDEX translationmessage__language__no_variant__submitter__idx
ON translationmessage (language, submitter)
WHERE (variant IS NULL);

-- Speed up local suggestions look-up by setting up a partial index
-- for messages which are neither is_current nor is_imported.
-- This should help because relation of unused TMs compared to used
-- is around 1/10.
-- XXX Danilo: previous index was not UNIQUE even if __key suggests it was.
CREATE INDEX tm__potmsgset__language__variant__not_used__idx
ON translationmessage (potmsgset, language, variant)
WHERE (NOT ((is_current IS TRUE) AND (is_imported IS TRUE)));

-- Indexes to fetch current messages: there can be at most one shared
-- (potemplate IS NULL) and one diverged (potemplate = X) is_current message.
-- Split into 4 to cope with NULL handling for potemplate and variant fields.
CREATE UNIQUE INDEX tm__potmsgset__language__no_variant__shared__current__key
ON translationmessage (potmsgset, language)
WHERE ((is_current IS TRUE) AND (potemplate IS NULL) AND (variant IS NULL));
CREATE UNIQUE INDEX tm__potmsgset__language__variant__shared__current__key
ON translationmessage (potmsgset, language, variant)
WHERE ((is_current IS TRUE) AND (potemplate IS NULL) AND (variant IS NOT NULL));
CREATE UNIQUE INDEX
    tm__potmsgset__potemplate__language__no_variant__diverged__current__key
ON translationmessage (potmsgset, potemplate, language, variant)
WHERE ((is_current IS TRUE) AND (potemplate IS NOT NULL) AND (variant IS NULL));
CREATE UNIQUE INDEX
    tm__potmsgset__potemplate__language__variant__diverged__current__key
ON translationmessage (potmsgset, potemplate, language, variant)
WHERE ((is_current IS TRUE) AND (potemplate IS NOT NULL)
    AND (variant IS NOT NULL));

-- Indexes to fetch imported messages: there can be at most one shared
-- (potemplate IS NULL) and one diverged (potemplate = X) is_imported message.
-- Split into 4 to cope with NULL handling for potemplate and variant fields.
CREATE UNIQUE INDEX tm__potmsgset__language__no_variant__shared__imported__key
ON translationmessage (potmsgset, language)
WHERE ((is_imported IS TRUE) AND (potemplate IS NULL) AND (variant IS NULL));
CREATE UNIQUE INDEX tm__potmsgset__language__variant__shared__imported__key
ON translationmessage (potmsgset, language, variant)
WHERE ((is_imported IS TRUE) AND (potemplate IS NULL)
    AND (variant IS NOT NULL));
CREATE UNIQUE INDEX
    tm__potmsgset__potemplate__language__no_variant__diverged__imported__key
ON translationmessage (potmsgset, potemplate, language, variant)
WHERE ((is_imported IS TRUE) AND (potemplate IS NOT NULL)
    AND (variant IS NULL));
CREATE UNIQUE INDEX
    tm__potmsgset__potemplate__language__variant__diverged__imported__key
ON translationmessage (potmsgset, potemplate, language, variant)
WHERE ((is_imported IS TRUE) AND (potemplate IS NOT NULL)
    AND (variant IS NOT NULL));

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 44, 2);

