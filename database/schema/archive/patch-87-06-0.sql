SET client_min_messages=ERROR;

CREATE TABLE BranchVisibilityPolicy
(
  id SERIAL PRIMARY KEY,
  project INT REFERENCES Project,
  product INT REFERENCES Product,
  team INT REFERENCES Person,
  policy INT NOT NULL DEFAULT 1,
  CONSTRAINT only_one_target CHECK (project IS NULL != product IS NULL)
);

CREATE UNIQUE INDEX branchvisibilitypolicy__unq ON BranchVisibilityPolicy(
    (COALESCE(product,-1)), (COALESCE(project,-1)), (COALESCE(team, -1))
);

CREATE INDEX branchvisibilitypolicy__team__idx
    ON BranchVisibilityPolicy(team) WHERE team IS NOT NULL;
CREATE INDEX branchvisibilitypolicy__project__idx
    ON BranchVisibilityPolicy(project) WHERE project IS NOT NULL;
CREATE INDEX branchvisibilitypolicy__product__idx
    ON BranchVisibilityPolicy(product) WHERE product IS NOT NULL;

ALTER TABLE Branch ADD COLUMN private BOOLEAN DEFAULT False NOT NULL;

CREATE INDEX branch__private__idx
    ON Branch(private);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 06, 0);
