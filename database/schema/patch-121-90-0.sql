SET client_min_messages=ERROR;

CREATE TABLE Job (
  id SERIAL PRIMARY KEY,
  lease_expires TIMESTAMP WITHOUT TIME ZONE
);


CREATE TABLE JobDependency (
  prerequisite INTEGER NOT NULL REFERENCES Job,
  dependant INTEGER NOT NULL REFERENCES Job,
  PRIMARY KEY (prerequisite, dependant)
);


CREATE TABLE StaticDiffJob (
  id SERIAL PRIMARY KEY,
  job INTEGER REFERENCES Job,
  branch INTEGER NOT NULL REFERENCES Branch,
  from_revision_spec TEXT,
  to_revision_spec TEXT,
  branch_merge_proposal INTEGER REFERENCES BranchMergeProposal
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


CREATE TABLE PreviewDiffReference (
  id SERIAL PRIMARY KEY,
  branch_merge_proposal INTEGER UNIQUE NOT NULL REFERENCES BranchMergeProposal,
  last_source_revision_id TEXT,
  last_target_revision_id TEXT,
  last_dependent_revision_id TEXT,
  diff INTEGER REFERENCES Diff,
  conflicts TEXT
);


CREATE TABLE CodeMailJob (
  id SERIAL PRIMARY KEY,
  job INTEGER REFERENCES Job,
  static_diff INTEGER REFERENCES StaticDiff,
  max_diff_lines INTEGER,
  from_address TEXT NOT NULL,
  reply_to_address TEXT,
  to_address TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  footer TEXT NOT NULL,
  rationale TEXT NOT NULL,
  branch_url TEXT NOT NULL,
  branch_project_name TEXT,
  date_created TIMESTAMP WITHOUT TIME ZONE NOT NULL
      DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  rfc822msgid TEXT NOT NULL,
  in_reply_to TEXT
);


ALTER TABLE BranchMergeProposal
  ADD COLUMN review_diff INTEGER REFERENCES StaticDiff;


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 90, 0);
