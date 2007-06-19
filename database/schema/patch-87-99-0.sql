SET client_min_messages=ERROR;

CREATE TABLE BranchLandingTarget
(
   id SERIAL PRIMARY KEY,
   registrant INT REFERENCES Person NOT NULL,
   source_branch INT REFERENCES Branch NOT NULL,
   target_branch INT REFERENCES Branch NOT NULL,
   date_created TIMESTAMP NOT NULL DEFAULT timezone('UTC'::text, now()),
   CONSTRAINT different_branches CHECK (source_branch != target_branch),
   UNIQUE(source_branch, target_branch)
);

COMMENT ON TABLE BranchLandingTarget IS 'Branch landing targets are showing intent of landing (or merging) one branch on another.';
COMMENT ON COLUMN BranchLandingTarget.registrant IS 'The person that created the landing target.';
COMMENT ON COLUMN BranchLandingTarget.source_branch IS 'The branch where the work is being written.  This branch contains the changes that the registrant wants to land.';
COMMENT ON COLUMN BranchLandingTarget.target_branch IS 'The branch where the user wants the changes from the source branch to be merged into.';
COMMENT ON COLUMN BranchLandingTarget.date_created IS 'When the registrant created the landing target.';

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);

