SET client_min_messages=ERROR;

CREATE TABLE BranchMergeProposal
(
   id SERIAL PRIMARY KEY,
   registrant INT REFERENCES Person NOT NULL,
   source_branch INT REFERENCES Branch NOT NULL,
   target_branch INT REFERENCES Branch NOT NULL,
   dependent_branch  INT REFERENCES Branch,
   whiteboard TEXT,
   date_created TIMESTAMP NOT NULL DEFAULT timezone('UTC'::text, now()),
   CONSTRAINT different_branches CHECK (source_branch != target_branch),
   UNIQUE(source_branch, target_branch)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);

