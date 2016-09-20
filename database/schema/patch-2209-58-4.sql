-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- STEP 7
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

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 58, 4);
