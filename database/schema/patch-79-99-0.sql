SET client_min_messages=ERROR;

CREATE TABLE BranchVisibilityPolicy
(
  id SERIAL PRIMARY KEY,
  project INT REFERENCES Project,
  product INT REFERENCES Product,
  team INT REFERENCES Person,
  policy INT NOT NULL DEFAULT 1,
  UNIQUE(project, pillar, team),
  CONSTRAINT only_one_target(
    project IS NOT NULL and product IS NULL or
    project IS NULL and product IS NOT NULL) 
);

COMMENT ON TABLE BranchVisibilityPolicy IS 'Defines the policy for the initial visibility of branches.';
COMMENT ON COLUMN BranchVisibilityPolicy.project IS 'Even though projects don\'t directly have branches themselves, if a product of the project does not specify its own branch visibility policies, those of the project are used.';
COMMENT ON COLUMN BranchVisibilityPolicy.product IS 'The product that the visibility policies apply to.';
COMMENT ON COLUMN BranchVisibilityPolicy.team IS 'Refers to the team that the policy applies to.  NULL is used to indicate ALL people, as there is no team defined for *everybody*.';
COMMENT ON COLUMN BranchVisibilityPolicy.policy IS 'An enumerated type, one of PUBLIC or PRIVATE.  PUBLIC is the default value.';


ALTER TABLE Branch ADD COLUMN visibility_team INTEGER
    REFERENCES Person;

COMMENT ON COLUMN Branch.visibility_team IS 'If NULL then the branch is visible to all, otherwise only members of the team specified can see the branch. If the specified Person is actually a person and not a team, then the branch is only visible to that person.';


INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);
