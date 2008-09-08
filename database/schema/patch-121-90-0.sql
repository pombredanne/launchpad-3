SET client_min_messages=ERROR;

CREATE TABLE Job (
  id serial PRIMARY KEY,
  lease_expires TIMESTAMP WITHOUT TIME ZONE
);


CREATE TABLE JobDependency ( -- Rows in this table describe dependencies between jobs.
  dependency INTEGER NOT NULL REFERENCES Job,
  dependant INTEGER NOT NULL REFERENCES Job,
  PRIMARY KEY (dependency, dependant)
);


CREATE TABLE StaticDiffJob ( -- Rows in this table are directions for producing a diff.
  id serial PRIMARY KEY,
  job integer REFERENCES Job,
  from_branch integer NOT NULL REFERENCES Branch,
  from_revision_spec text,
  to_revision_spec text,
  to_branch integer NOT NULL REFERENCES Branch,
  lease timestamp without time zone
);


CREATE TABLE Diff ( -- Contains information about static and preview diffs
  id serial PRIMARY KEY,
  diff_text integer NOT NULL REFERENCES LibraryFileAlias,
  diff_lines_count integer,
  diffstat text,
  added_lines_count integer,
  removed_lines_count integer
);


CREATE TABLE StaticDiff ( -- Contains information about static diffs
  id serial PRIMARY KEY,
  range_start TEXT, -- a revision-id
  range_end TEXT, -- a revision-id
  diff integer REFERENCES Diff,
  UNIQUE (range_start, range_end)
);


CREATE TABLE PreviewDiffReference ( -- Contains information about preview diffs, but does not duplicate information with BranchMergeProposal
  id serial PRIMARY KEY,
  branch_merge_proposal integer UNIQUE NOT NULL REFERENCES BranchMergeProposal,
  last_source_revision integer NOT NULL REFERENCES Revision,
  last_target_revision integer NOT NULL REFERENCES Revision,
  last_dependent_revision integer REFERENCES Revision,
  diff integer REFERENCES Diff,
  conflicts text -- perhaps BYTES, store serialised bzrlib obj or not?
);


CREATE TABLE CodeMailJob (
  id serial PRIMARY KEY,
  job integer REFERENCES Job,
  static_diff integer REFERENCES StaticDiff,
  from_address text NOT NULL,
  reply_to_address text,
  to_address text NOT NULL,
  subject text NOT NULL,
  body text NOT NULL,
  footer text NOT NULL,
  rationale text NOT NULL,
  branch_url text NOT NULL,
  branch_project_name text,
  date_created timestamp without time zone NOT NULL
      DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  rfc822msgid text NOT NULL,
  in_reply_to text -- A Message-Id
);


ALTER TABLE BranchMergeProposal
  ADD COLUMN review_diff integer REFERENCES StaticDiff;


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 90, 0);
