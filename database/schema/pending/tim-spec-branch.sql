CREATE TABLE specificationbranch (
    id serial NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    specification integer NOT NULL,
    branch integer NOT NULL
);

ALTER TABLE ONLY specificationbranch
    ADD CONSTRAINT specification_branch_unique UNIQUE (specification, branch);

ALTER TABLE ONLY specificationbranch
    ADD CONSTRAINT specificationbranch_branch_fkey FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY specificationbranch
    ADD CONSTRAINT specificationbranch_specification_fkey FOREIGN KEY (specification) REFERENCES specification(id);




INSERT INTO LaunchpadDatabaseRevision VALUES (67, 99, 9);

