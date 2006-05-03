SET client_min_messages=error;

-- ensure that a particular revision does not occur multiple times in
-- the history of a branch.
ALTER TABLE RevisionNumber
  ADD CONSTRAINT revisionnumber_branch_revision_unique
    UNIQUE (branch, revision);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 96, 0);
