SET client_min_messages=ERROR;

ALTER TABLE BranchMergeProposal
  ADD COLUMN superseded_by INT REFERENCES BranchMergeProposal;

-- This constraint is no longer correct and a database level
-- constraint isn't going to help now due to model changes.
ALTER TABLE BranchMergeProposal
  DROP CONSTRAINT branchmergeproposal_source_branch_key;

CREATE INDEX branchmergeproposal__superseded_by__idx
  ON BranchMergeProposal(superseded_by) WHERE superseded_by IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 10, 0);
