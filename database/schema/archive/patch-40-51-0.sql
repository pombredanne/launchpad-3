SET client_min_messages=ERROR;

-- Too permissive. Superceded by the new constraints.
ALTER TABLE RevisionNumber DROP CONSTRAINT revisionnumber_unique;

-- All RevisionNumbers for a branch must have distinct sequence numbers.
ALTER TABLE RevisionNumber ADD CONSTRAINT revisionnumber_branch_sequence_unique
    UNIQUE (branch, sequence);

-- A revision may appear at most once in the history of a branch.
ALTER TABLE RevisionNumber ADD CONSTRAINT revisionnumber_revision_branch_unique
    UNIQUE (revision, branch);

-- FIXME: get a real database patch number
INSERT INTO LaunchpadDatabaseRevision VALUES (40, 51, 0);
