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
  date_finished TIMESTAMP WITHOUT TIME ZONE
);

-- For person merge.
CREATE INDEX job__requester__key
    ON Job (requester)
    WHERE (requester IS NOT NULL);


CREATE TABLE BranchJob (
  id SERIAL PRIMARY KEY,
  job INTEGER NOT NULL REFERENCES Job,
  branch INTEGER NOT NULL REFERENCES Branch,
  job_type INTEGER NOT NULL,
  json_data TEXT
);

CREATE TABLE BranchMergeProposalJob (
  id SERIAL PRIMARY KEY,
  job INTEGER NOT NULL REFERENCES Job,
  branch_merge_proposal INTEGER NOT NULL REFERENCES BranchMergeProposal,
  job_type INTEGER NOT NULL,
  json_data TEXT
);

CREATE TABLE MergeDirectiveJob (
  id SERIAL PRIMARY KEY,
  job INTEGER NOT NULL REFERENCES Job,
  message INTEGER NOT NULL REFERENCES LibraryFileAlias,
  action INTEGER
);

CREATE TABLE Diff (
  id serial PRIMARY KEY,
  diff_text INTEGER NOT NULL REFERENCES LibraryFileAlias,
  diff_lines_count INTEGER,
  diffstat TEXT,
  added_lines_count INTEGER,
  removed_lines_count INTEGER
);

CREATE TABLE StaticDiff (
  id serial PRIMARY KEY,
  from_revision_id TEXT,
  to_revision_id TEXT,
  diff INTEGER REFERENCES Diff,
  UNIQUE (from_revision_id, to_revision_id)
);

CREATE TABLE PreviewDiff (
  id SERIAL PRIMARY KEY,
  source_revision_id TEXT,
  target_revision_id TEXT,
  dependent_revision_id TEXT,
  diff INTEGER REFERENCES Diff,
  conflicts TEXT
);


ALTER TABLE BranchMergeProposal
  ADD COLUMN review_diff INTEGER REFERENCES StaticDiff;
ALTER TABLE BranchMergeProposal
  ADD COLUMN merge_diff INTEGER REFERENCES PreviewDiff;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 90, 0);
