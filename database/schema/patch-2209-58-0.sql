-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- STEP 1, DB PATCH 1
-- Add the new wide column to LibraryFileContent.
-- We can't do LibraryFileAlias yet, as we want to create it with the
-- foreign key defined, and for that we need a UNIQUE index on LFC._id,
-- and we need to create that CONCURRENTLY to avoid downtime.
--
ALTER TABLE LibraryFileContent ADD COLUMN _id bigint;

-- LibraryFileContent needs an INSERT trigger, ensuring that new
-- records get a LFC._id matching LFC.id
CREATE FUNCTION lfc_sync_id_t() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW._id := NEW.id;
    RETURN NEW;
END;
$$;

CREATE TRIGGER lfc_sync_id_t BEFORE INSERT ON LibraryFileContent
FOR EACH ROW EXECUTE PROCEDURE lfc_sync_id_t();

-- We don't need this partial index in addition to the full one,
-- The partial is hit 3x more often than the full, but only once
-- per day almost certainly by the garbage collector so it isn't
-- worth maintaining both.
DROP INDEX libraryfilealias__expires_content_not_null_idx;


/* Subsequent statements, to be executed live and in subsequent patches
 * after timing and optimization.
 */

/*
-- STEP 2, LIVE
-- Backfill LFC._id, but do so in small batches.
UPDATE LibraryFileContent SET _id=id WHERE _id IS NULL;


-- STEP 3, LIVE
-- To be done CONCURRENTLY, create the UNIQUE index on LFC._id.
CREATE UNIQUE INDEX libraryfilecontent_id_key ON LibraryFileContent(_id);


-- STEP 4, DB PATCH 2.
-- Add the new wide column to LibraryFileAlias, as a foreign key reference
-- to LFC._id
ALTER TABLE LibraryFileAlias
    ADD COLUMN _content bigint REFERENCES LibraryFileContent(_id);

-- LibraryFileAlias needs an INSERT and UPDATE trigger, ensuring that
-- LFA.content is synced with LFA._content. We have already backfilled
-- LFC._id, so we can guarantee inserts will not fail due to FK violation.
CREATE FUNCTION lfa_sync_content_t() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW._content := NEW.content;
    RETURN NEW;
END;
$$;

CREATE TRIGGER lfa_sync_content_t BEFORE INSERT OR UPDATE ON LibraryFileAlias
FOR EACH ROW EXECUTE PROCEDURE lfa_sync_content_t();


-- STEP 5, LIVE.
-- Backfill LFA._contentFill in new columns, but do it in batches.
UPDATE LibraryFileAlias SET _content = content;


-- STEP 6, LIVE.
-- LibraryFileAlias indexes, to be done concurrently.
CREATE INDEX libraryfilealias__content__idx ON LibraryFileAlias(_content);


-- STEP 7, DB PATCH 3.
-- Constraints, swap into place, and the rest.

-- Explicitly grab the lock since we will be bypassing DDL and going
-- straight to the catalog.
LOCK LibraryFileContent, LibraryFileAlias;

-- Set LFC._id and LFC.sha256 to NOT NULL, the sneaky unsupported way.
UPDATE pg_attribute SET attnotnull=TRUE
FROM pg_class, pg_namespace
WHERE
    pg_class.oid = pg_attribute.attrelid
    AND pg_namespace.oid = pg_class.relnamespace
    AND pg_attribute.attname in ('_id', 'sha256')
    AND pg_namespace.nspname = 'public'
    AND pg_class.relname = 'libraryfilecontent';

-- Kill the triggers.
DROP TRIGGER lfa_sync_content_t ON LibraryFileAlias;
DROP TRIGGER lfc_sync_id_t ON LibraryFileContent;
DROP FUNCTION lfa_sync_content_t();
DROP FUNCTION lfc_sync_id_t();

-- Fix the SEQUENCE owner, so it doesn't get removed when the old id column
-- is dropped.
ALTER SEQUENCE libraryfilecontent_id_seq OWNED BY LibraryFileContent._id;

-- Swap in the wide columns.
ALTER TABLE LibraryFileAlias DROP COLUMN content;
ALTER TABLE LibraryFileAlias RENAME _content TO content;
ALTER TABLE LibraryFileContent DROP COLUMN id;
ALTER TABLE LibraryFileContent RENAME _id TO id;

-- Fixup the LFC primary key.
ALTER INDEX libraryfilecontent_id_key RENAME TO libraryfilecontent_pkey;
ALTER TABLE LibraryFileContent
    ALTER COLUMN id SET DEFAULT nextval('libraryfilecontent_id_seq'),
    ADD CONSTRAINT libraryfilecontent_pkey
        PRIMARY KEY USING INDEX libraryfilecontent_pkey; -- Maybe slow.

*/
INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 58, 0);
