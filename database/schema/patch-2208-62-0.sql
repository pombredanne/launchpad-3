BEGIN;

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

-- The primary key constraint is on different columns now.
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
        SELECT oid FROM pg_class
        WHERE relname='revision__revision__branch__key')
WHERE refobjid = (
    SELECT pg_constraint.oid FROM pg_constraint, pg_class
    WHERE 
        pg_class.oid = pg_constraint.conrelid
        AND contype='p'
        AND relname='branchrevision')
    AND objid = (SELECT oid FROM pg_class WHERE relname='revisionnumber_pkey');

-- Delete old dependency between the constraint and the table columns.
DELETE FROM pg_depend
WHERE
    classid = (SELECT oid FROM pg_class WHERE relname='pg_constraint')
    AND objid = (
        SELECT pg_constraint.oid FROM pg_constraint, pg_class
        WHERE
            pg_class.oid = pg_constraint.conrelid
            AND contype='p'
            AND relname='branchrevision')
    AND refclassid = (SELECT oid FROM pg_class WHERE relname='pg_class')
    AND refobjid = (SELECT oid FROM pg_class WHERE relname='branchrevision')
    AND deptype = 'a';

-- Transfer dependencies of the new key's index on its table
-- columns to the constraint. It depends on the columns now.
UPDATE pg_depend
SET
    classid = (SELECT oid FROM pg_class WHERE relname='pg_constraint'),
    objid = (
        SELECT pg_constraint.oid FROM pg_constraint, pg_class
        WHERE
            pg_class.oid = pg_constraint.conrelid
            AND contype='p'
            AND relname='branchrevision')
WHERE
    classid = (SELECT oid FROM pg_class WHERE relname='pg_class')
    AND objid = (
        SELECT oid FROM pg_class
        WHERE relname='revision__revision__branch__key')
    AND refclassid = (SELECT oid FROM pg_class WHERE relname='pg_class')
    AND refobjid = (select oid FROM pg_class WHERE relname='branchrevision')
    AND deptype = 'a';

-- Delete the old UNIQUE constraint.
DELETE FROM pg_constraint
WHERE conname='revision__revision__branch__key' AND contype='u';

-- This view is no longer used - no need to recreate it.
DROP VIEW RevisionNumber;

-- Need to drop this manually as we have repurposed the pg_dependency
-- between the id column and this index.
DROP INDEX revisionnumber_pkey;

ALTER TABLE BranchRevision
    DROP COLUMN id,
    DROP CONSTRAINT revision__branch__revision__key;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);

