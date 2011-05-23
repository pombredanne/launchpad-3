BEGIN;

-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

-- Make the existing primary key index think it is not the primary key.
UPDATE pg_index SET indisprimary = FALSE
WHERE pg_index.indexrelid = 'revisionnumber_pkey'::regclass;


-- Make an existing index think it is the primary key.
UPDATE pg_index SET indisprimary = TRUE
WHERE pg_index.indexrelid = 'revision__revision__branch__key'::regclass;


-- The primary key constraint is on different columns now.
UPDATE pg_constraint SET
    conname='revision__revision__branch__key',
    conkey='{4,3}'
WHERE
    contype='p'
    AND pg_constraint.conrelid = 'branchrevision'::regclass;


-- The primary key constraint now depends on the new index
UPDATE pg_depend
    SET objid='revision__revision__branch__key'::regclass
WHERE
    objid = 'revisionnumber_pkey'::regclass
    AND refobjid = (
        SELECT pg_constraint.oid FROM pg_constraint
        WHERE
            contype='p'
            AND pg_constraint.conrelid = 'branchrevision'::regclass);


-- Delete old dependency between the constraint and the table columns.
DELETE FROM pg_depend
WHERE
    classid = 'pg_constraint'::regclass
    AND objid = (
        SELECT pg_constraint.oid FROM pg_constraint
        WHERE
            contype='p'
            AND pg_constraint.conrelid = 'branchrevision'::regclass)
    AND refclassid = 'pg_class'::regclass
    AND refobjid = 'branchrevision'::regclass
    AND deptype = 'a';

-- Transfer dependencies of the new key's index on its table
-- columns to the constraint. It depends on the columns now.
UPDATE pg_depend
SET
    classid = 'pg_constraint'::regclass,
    objid = (
        SELECT pg_constraint.oid FROM pg_constraint
        WHERE
            contype='p'
            AND pg_constraint.conrelid = 'branchrevision'::regclass)
WHERE
    classid = 'pg_class'::regclass
    AND objid = 'revision__revision__branch__key'::regclass
    AND refclassid = 'pg_class'::regclass
    AND refobjid = 'branchrevision'::regclass
    AND deptype = 'a';

-- Delete the old UNIQUE constraint.
-- XXX: This fails! If we dump the database after applying this patch,
-- the dump attempts to create both a primary key and a unique constraint
-- with the same name on the same columns.
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

