/* As per a discussion earlier today with Mark we want to unify
   *BugAssignment's into one table. Aggregating package/product assignments
   into one listing, sorted on bug ID and date is Just Too Slow when working
   with SQLObject + two separate db entities, which is why I propose the
   following patch to merge them, consistent with what Mark and I discussed. */

/* table definition */
CREATE TABLE bugassignment (
    id serial NOT NULL,
    bug integer NOT NULL,
    product integer,
    sourcepackagename integer,
    distro integer,
    status integer NOT NULL,
    priority integer NOT NULL,
    severity integer NOT NULL,
    binarypackagename integer,
    assignee integer,
    dateassigned timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);

/* constraints */
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bugassignment_pkey PRIMARY KEY (id);
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bugassignment_bug_key UNIQUE (bug, sourcepackagename, distro);
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bugassignment_bug_key UNIQUE (bug, product);
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bug_fk FOREIGN KEY (bug) REFERENCES bug(id);
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT distro_fk FOREIGN KEY (distro) REFERENCES distribution(id);
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT person_fk FOREIGN KEY (assignee) REFERENCES person(id);
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT product_fk FOREIGN KEY (product) REFERENCES product(id);
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bugassignment_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bugassignment_one_assignment CHECK (
        (product is null) or
        (sourcepackagename is null and distro is null));

/* indexes */
CREATE INDEX bugassignment_owner_idx ON bugassignment USING btree ("owner");

/* comments */
COMMENT ON TABLE bugassignment IS 'Links a given Bug to a particular (sourcepackagename, distro) or product.';
COMMENT ON COLUMN bugassignment.bug IS 'The bug that is assigned to this (sourcepackagename, distro) or product.';
COMMENT ON COLUMN bugassignment.product IS 'The product in which this bug shows up.';
COMMENT ON COLUMN bugassignment.sourcepackagename IS 'The name of the sourcepackage in which this bug shows up.';
COMMENT ON COLUMN bugassignment.distro IS 'The distro of the named sourcepackage.';
COMMENT ON COLUMN bugassignment.status IS 'The general health of the bug, e.g. Accepted, Rejected, etc.';
COMMENT ON COLUMN bugassignment.priority IS 'The importance of fixing this bug.';
COMMENT ON COLUMN bugassignment.severity IS 'The impact of this bug.';
COMMENT ON COLUMN bugassignment.binarypackagename IS 'The name of the binary package built from the source package.';
COMMENT ON COLUMN bugassignment.assignee IS 'The person who has been assigned to fix this bug in this product or (sourcepackagename, distro)';
COMMENT ON COLUMN bugassignment.dateassigned IS 'The date on which the bug in this (sourcepackagename, distro) or product was assigned to someone to fix';
COMMENT ON COLUMN bugassignment.datecreated IS 'A timestamp for the creation of this bug assignment. Note that this is not the date the bug was created (though it might be), it''s the date the bug was assigned to this product, which could have come later.';

/* migrate existing product assignments */
INSERT INTO bugassignment (
    bug, product, status, priority, severity,
    assignee, dateassigned, datecreated, owner)
SELECT bug, product, bugstatus, priority, severity, assignee,
       dateassigned, datecreated, owner 
FROM productbugassignment;

/* migrate existing package assignments */
INSERT INTO bugassignment (
    bug, sourcepackagename, distro, status, priority, 
    severity, binarypackagename, assignee, dateassigned, 
    datecreated, owner)
SELECT bug, sourcepackagename, distro, bugstatus, priority, severity,
       binarypackagename, assignee, dateassigned, datecreated, owner
FROM sourcepackagebugassignment spba, sourcepackage sp, sourcepackagename spn
WHERE spba.sourcepackage = sp.id and sp.sourcepackagename = spn.id;
