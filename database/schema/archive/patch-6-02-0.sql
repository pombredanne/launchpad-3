SET client_min_messages=ERROR;

/* Old or new values might be NULL */
ALTER TABLE BugActivity ALTER COLUMN oldvalue DROP NOT NULL;
ALTER TABLE BugActivity ALTER COLUMN newvalue DROP NOT NULL;

/* Rename a key */
ALTER TABLE Project DROP CONSTRAINT "$1";
ALTER TABLE Project ADD CONSTRAINT project_owner_fk
    FOREIGN KEY("owner") REFERENCES Person(id);

/* As per a discussion earlier today with Mark we want to unify
   *BugAssignment's into one table. Aggregating package/product assignments
   into one listing, sorted on bug ID and date is Just Too Slow when working
   with SQLObject + two separate db entities, which is why I propose the
   following patch to merge them, consistent with what Mark and I discussed. */

/* table definition */
CREATE TABLE BugAssignment (
    id serial PRIMARY KEY,
    bug integer NOT NULL,
    product integer,
    sourcepackagename integer,
    distro integer,
    status integer NOT NULL,
    priority integer NOT NULL,
    severity integer NOT NULL,
    binarypackagename integer,
    assignee integer,
    dateassigned timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    datecreated timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    "owner" integer NOT NULL
);

/* constraints */
ALTER TABLE ONLY bugassignment ADD CONSTRAINT bugassignment_distro_key
    UNIQUE (distro, sourcepackagename, bug);

ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bugassignment_product_key UNIQUE (product, bug);

ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bugassignment_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugassignment ADD CONSTRAINT bugassignment_distro_fk
    FOREIGN KEY (distro) REFERENCES distribution(id);

ALTER TABLE ONLY bugassignment ADD CONSTRAINT bugassignment_sourcepackagename_fk
    FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY bugassignment ADD CONSTRAINT bugassignment_person_fk
    FOREIGN KEY (assignee) REFERENCES person(id);

ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bugassignment_binarypackagename_fk
    FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);
    
ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bugassignment_product_fk FOREIGN KEY (product)
    REFERENCES product(id);

ALTER TABLE ONLY bugassignment
    ADD CONSTRAINT bugassignment_owner_fk
    FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY bugassignment ADD CONSTRAINT bugassignment_assignment_checks
    CHECK (
        (product IS NULL <> sourcepackagename IS NULL) AND
        (distro IS NULL = sourcepackagename IS NULL) AND
        (binarypackagename IS NULL OR sourcepackagename IS NOT NULL)
        );

/* indexes */
CREATE INDEX bugassignment_owner_idx ON bugassignment("owner");
CREATE INDEX bugassignment_assignee_idx ON bugassignment(assignee);

UPDATE LaunchpadDatabaseRevision SET major=6,minor=2,patch=0;

