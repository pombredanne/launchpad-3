-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE Job (
  id SERIAL PRIMARY KEY,
  requester INTEGER REFERENCES Person,
  reason TEXT,
  -- Status and progress
  status INTEGER NOT NULL,
  progress INTEGER, -- in percent
  -- Progress reporting
  last_report_seen TIMESTAMP WITHOUT TIME ZONE,
  next_report_due TIMESTAMP WITHOUT TIME ZONE,
  -- Retries
  attempt_count INTEGER NOT NULL DEFAULT 0,
  max_retries INTEGER NOT NULL DEFAULT 0,
  -- Log tail of the job (optional)
  log TEXT,
  -- Future jobs
  scheduled_start TIMESTAMP WITHOUT TIME ZONE,
  -- Job Lease
  lease_expires TIMESTAMP WITHOUT TIME ZONE,
  -- Creation and duration
  date_created TIMESTAMP WITHOUT TIME ZONE NOT NULL
      DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  date_started TIMESTAMP WITHOUT TIME ZONE,
  date_finished TIMESTAMP WITHOUT TIME ZONE,
  -- For selecting
  CONSTRAINT job__status__id__key UNIQUE (status, id)
);

-- For person merge.
CREATE INDEX job__requester__key
    ON Job (requester)
    WHERE (requester IS NOT NULL);

CREATE TABLE BranchJob (
  id SERIAL PRIMARY KEY,
  job INTEGER NOT NULL REFERENCES Job ON DELETE CASCADE UNIQUE,
  branch INTEGER NOT NULL REFERENCES Branch,
  job_type INTEGER NOT NULL,
  json_data TEXT
);

CREATE INDEX branchjob__branch__idx ON BranchJob(branch);

CREATE TABLE BranchMergeProposalJob (
  id SERIAL PRIMARY KEY,
  job INTEGER NOT NULL REFERENCES Job ON DELETE CASCADE UNIQUE,
  branch_merge_proposal INTEGER NOT NULL REFERENCES BranchMergeProposal,
  job_type INTEGER NOT NULL,
  json_data TEXT
);

CREATE INDEX branchmergeproposaljob__branch_merge_proposal__idx
    ON BranchMergeProposalJob(branch_merge_proposal);

CREATE TABLE MergeDirectiveJob (
  id SERIAL PRIMARY KEY,
  job INTEGER NOT NULL REFERENCES Job ON DELETE CASCADE UNIQUE,
  merge_directive INTEGER NOT NULL REFERENCES LibraryFileAlias,
  action INTEGER NOT NULL
);

CREATE INDEX mergedirectivejob__merge_directive__idx
    ON MergeDirectiveJob(merge_directive);

CREATE TABLE Diff (
  id serial PRIMARY KEY,
  diff_text INTEGER REFERENCES LibraryFileAlias,
  diff_lines_count INTEGER,
  diffstat TEXT,
  added_lines_count INTEGER,
  removed_lines_count INTEGER
);

CREATE INDEX diff__diff_text__idx ON Diff(diff_text);

CREATE TABLE StaticDiff (
  id serial PRIMARY KEY,
  from_revision_id TEXT NOT NULL,
  to_revision_id TEXT NOT NULL,
  diff INTEGER REFERENCES Diff ON DELETE CASCADE NOT NULL,
  UNIQUE (from_revision_id, to_revision_id)
);

CREATE INDEX staticdiff__diff__idx ON StaticDiff(diff);

CREATE TABLE PreviewDiff (
  id SERIAL PRIMARY KEY,
  source_revision_id TEXT NOT NULL,
  target_revision_id TEXT NOT NULL,
  dependent_revision_id TEXT NOT NULL,
  diff INTEGER REFERENCES Diff ON DELETE CASCADE NOT NULL,
  conflicts TEXT
);

CREATE INDEX previewdiff__diff__idx ON PreviewDiff(diff);

ALTER TABLE BranchMergeProposal
  ADD COLUMN review_diff INTEGER REFERENCES StaticDiff;
ALTER TABLE BranchMergeProposal
  ADD COLUMN merge_diff INTEGER REFERENCES PreviewDiff;

CREATE INDEX branchmergeproposal__review_diff__idx
    ON BranchMergeProposal(review_diff);
CREATE INDEX branchmergeproposal__merge_diff__idx
    ON BranchMergeProposal(merge_diff);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 11, 0);

