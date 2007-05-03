SET client_min_messages=ERROR;

CREATE TABLE BranchVisibilityPolicy
(
  id SERIAL PRIMARY KEY,
  pillar INT REFERENCES PillarName NOT NULL,
  team INT REFERENCES Person,
  policy INT NOT NULL DEFAULT 1,
  UNIQUE(pillar, visibility_team)
);

COMMENT ON TABLE BranchVisibilityPolicy IS 'Defines the policy for the initial visibility of branches.';
COMMENT ON COLUMN BranchVisibilityPolicy.pillar IS 'Refers to the pillar that has the branch privacy.';
COMMENT ON COLUMN BranchVisibilityPolicy.team IS 'Refers to the team that the policy applies to.  NULL is used to indicate ALL people, as there is no team defined for *everybody*.';
COMMENT ON COLUMN BranchVisibilityPolicy.policy IS 'An enumerated type, one of PUBLIC or PRIVATE.  PUBLIC is the default value.';


ALTER TABLE Branch ADD COLUMN visibility_team INTEGER
    REFERENCES Person;

COMMENT ON COLUMN Branch.visibility_team IS 'If NULL then the branch is visible to all, otherwise only members of the team specified can see the branch. If the specified Person is actually a person and not a team, then the branch is only visible to that person.';


INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);
