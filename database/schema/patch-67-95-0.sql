SET client_min_messages=ERROR;

CREATE TABLE specificationbranch (
  id serial NOT NULL,
  datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
  specification integer NOT NULL,
  branch integer NOT NULL,
  summary text NULL
);

ALTER TABLE ONLY specificationbranch
  ADD CONSTRAINT specificationbranch__spec_branch_unique
    UNIQUE (specification, branch);

ALTER TABLE ONLY specificationbranch
  ADD CONSTRAINT specificationbranch__branch__fk
    FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY specificationbranch
  ADD CONSTRAINT specificationbranch__specification__fk
    FOREIGN KEY (specification) REFERENCES specification(id);


INSERT INTO LaunchpadDatabaseRevision VALUES (67, 95, 0);
