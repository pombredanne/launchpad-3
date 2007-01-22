SET client_min_messages=ERROR;

CREATE TABLE specificationbranch (
  id serial PRIMARY KEY,
  datecreated timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
  specification integer NOT NULL,
  branch integer NOT NULL,
  summary text NULL
);

ALTER TABLE ONLY specificationbranch
  ADD CONSTRAINT specificationbranch__spec_branch_unique
    UNIQUE (branch, specification);

ALTER TABLE ONLY specificationbranch
  ADD CONSTRAINT specificationbranch__branch__fk
    FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY specificationbranch
  ADD CONSTRAINT specificationbranch__specification__fk
    FOREIGN KEY (specification) REFERENCES specification(id);

CREATE INDEX specificationbranch__specification__idx
  ON SpecificationBranch(specification);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 31, 0);
