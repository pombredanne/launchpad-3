-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- This constraint is useless given the current PK
ALTER TABLE BranchRevision
DROP CONSTRAINT revisionnumber_branch_id_unique;

-- This constraint is no longer needed as it will be the new PK
ALTER TABLE BranchRevision
DROP CONSTRAINT revision__branch__revision__key ;

-- This constraint is useless given the previous constraint
ALTER TABLE BranchRevision
DROP CONSTRAINT revision__revision__branch__key ;

-- Kill the old PK
ALTER TABLE BranchRevision
DROP CONSTRAINT revisionnumber_pkey ;

-- Create the new PK
ALTER TABLE BranchRevision
ADD CONSTRAINT revisionnumber_pkey PRIMARY KEY (branch, revision);

-- What was this used for?  Not used now.
DROP VIEW RevisionNumber;

-- Kill the old id.
ALTER TABLE BranchRevision
DROP COLUMN id;


INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
