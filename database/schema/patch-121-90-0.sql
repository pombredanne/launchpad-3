SET client_min_messages=ERROR;


CREATE TABLE Diff (
  id serial PRIMARY KEY,
  bytes integer NOT NULL REFERENCES LibraryFileAlias,
  diff_lines integer,
  diffstat text,
  added_lines integer,
  removed_lines integer,
  conflicts text
);


CREATE TABLE StaticDiffReference (
  id serial PRIMARY KEY,
  diff integer REFERENCES Diff,
  branch integer NOT NULL REFERENCES Branch,
  from_revision_spec text,
  to_revision_spec text,
  lease timestamp without time zone
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
  in_reply_to text NOT NULL, -- A Message-Id
  static_diff integer REFERENCES StaticDiffReference
  );


ALTER TABLE BranchMergeProposal
  ADD COLUMN review_diff integer REFERENCES StaticDiffReference;



INSERT INTO LaunchpadDatabaseRevision VALUES (121, 90, 0);
