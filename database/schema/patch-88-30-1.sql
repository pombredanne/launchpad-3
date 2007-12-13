SET client_min_messages=ERROR;

-- This index was created to avoid a regresion where queries optimized
-- for PG 8.2.5 where performing badly on the PG 8.2.3 DB.
-- It should no longer be required now everything is running 8.2.5,
-- but it does seem to still be improving performance of some queries anyway.
-- We should drop this index - if we still want the performance boost,
-- we should rewrite the relevant Rosetta queries to use is_fuzzy IS FALSE
-- instead of is_fuzzy IS NOT TRUE and rebuild the index with a better
-- name.
CREATE INDEX 
    translationmessage__83fix2__idx ON TranslationMessage (potmsgset)
WHERE (is_current IS TRUE OR is_imported IS TRUE) AND is_fuzzy IS NOT TRUE;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 30, 1);

