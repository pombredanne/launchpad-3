-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE BranchRevision
    DROP CONSTRAINT branchrevision__branch__fk,
    DROP CONSTRAINT branchrevision__revision__fk;
ALTER TABLE BranchRevision
    ADD CONSTRAINT branchrevision__branch__fk
    FOREIGN KEY (branch) REFERENCES Branch
    ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED,
    ADD CONSTRAINT branchrevision__revision__fk
    FOREIGN KEY (revision) REFERENCES Revision
    ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED;

-- Index to allow quick access to MIN(id) WHERE revision_date > ....
-- We use this to roughly filter BranchRevision on date to make the
-- real join with Revision faster.
ALTER TABLE Revision
   ADD CONSTRAINT revision__id__revision_date__key
   UNIQUE (id, revision_date);

-- Index to allow quick filtering of BranchRevision by branch and revision.
-- Note that existing UNIQUE (revision, branch) isn't used for this (we
-- generally have a very wide filter on revision, such as all revisions in the
-- last 30 days).
ALTER TABLE BranchRevision
   -- Branch -> Revision traversal
   ADD CONSTRAINT revision__branch__revision__key UNIQUE (branch, revision),
   -- Revision -> Branch traversal
   DROP CONSTRAINT revisionnumber_revision_branch_unique,
   ADD CONSTRAINT revision__revision__branch__key UNIQUE (revision, branch);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 14, 0);
