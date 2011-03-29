-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

-- Make the existing primary key index think it is not the primary key.
UPDATE pg_index SET indisprimary = FALSE
FROM pg_class
WHERE pg_class.oid = pg_index.indexrelid
    AND relname='revisionnumber_pkey';

-- Make an existing index think it is the primary key.
UPDATE pg_index SET indisprimary = TRUE
FROM pg_class
WHERE
    pg_class.oid = pg_index.indexrelid
    AND relname='revision__revision__branch__key';

-- Update the primary key constraint to point to the new index.
UPDATE pg_constraint SET
    conname='revision__revision__branch__key',
    conkey='{4,3}'
FROM pg_class
WHERE pg_class.oid = pg_constraint.conrelid
    AND contype='p'
    AND relname='branchrevision';

-- The primary key constraint now depends on the new index
UPDATE pg_depend
    SET objid=(
            SELECT indexrelid FROM pg_index, pg_class
            WHERE
                pg_index.indexrelid = pg_class.oid
                AND relname='revision__revision__branch__key')
WHERE refobjid = (
    SELECT pg_constraint.oid FROM pg_constraint, pg_class
    WHERE 
        pg_class.oid = pg_constraint.conrelid
        AND contype='p'
        AND relname='branchrevision');


-- Strip the unnecessary crud.
DROP VIEW RevisionNumber;

-- Need to drop explicitly. Why?
DROP INDEX revisionnumber_pkey;

ALTER TABLE BranchRevision
    DROP COLUMN id,
    DROP CONSTRAINT revision__branch__revision__key;


And fail...

ALTER TABLE BranchRevision DROP CONSTRAINT revision__revision__branch__key
does not work.

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
