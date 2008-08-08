SET client_min_messages=ERROR;


CREATE TABLE Diff (
  id serial PRIMARY KEY,
  diff_text integer NOT NULL REFERENCES LibraryFileAlias,
  diff_lines_count integer,
  diffstat text,
  added_lines_count integer,
  removed_lines_count integer,
  conflicts text -- perhpas BYTES, store serialised bzrlib obj or not?
);


CREATE TABLE StaticDiffReference (
  id serial PRIMARY KEY,
  branch integer NOT NULL REFERENCES Branch,
  from_revision_spec text,
  to_revision_spec text,
  diff integer REFERENCES Diff, -- this is populated by the thing that takes the lease
  lease timestamp without time zone
);


CREATE TABLE PreviewDiffReference (
  id serial PRIMARY KEY,
  branch_merge_proposal integer NOT NULL REFERENCES BranchMergeProposal, -- UNIQUE?
  last_source_revision integer NOT NULL REFERENCES Revision,
  last_target_revision integer NOT NULL REFERENCES Revision,
  last_dependent_revision integer REFERENCES Revision,
  diff integer REFERENCES Diff,
  lease timestamp without time zone,
);


CREATE TABLE PendingCodeMail (
  id serial PRIMARY KEY,
  from_address text NOT NULL,
  to_address text NOT NULL,
  subject text NOT NULL,
  body text NOT NULL,
  footer text NOT NULL,
  rationale text NOT NULL,
  branch_url text NOT NULL,
  date_created timestamp without time zone NOT NULL
      DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  rfc822msgid text NOT NULL,
  in_reply_to text, -- A Message-Id
  static_diff integer REFERENCES StaticDiffReference
  );


ALTER TABLE BranchMergeProposal
  ADD COLUMN review_diff integer REFERENCES StaticDiffReference;


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 90, 0);
