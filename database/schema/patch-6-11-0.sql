SET client_min_messages=ERROR;

DROP TABLE BugAssignment;

/* table definition */
CREATE TABLE BugTask (
    id serial PRIMARY KEY,
    bug integer NOT NULL,
    product integer,
    distribution integer,
    distrorelease integer,
    sourcepackagename integer,
    binarypackagename integer,
    status integer NOT NULL,
    priority integer NOT NULL,
    severity integer NOT NULL,
    assignee integer,
    dateassigned timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    datecreated timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    "owner" integer NOT NULL
);

/* foreign key constraints */
ALTER TABLE ONLY BugTask
    ADD CONSTRAINT bugtask_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);
ALTER TABLE ONLY BugTask
    ADD CONSTRAINT bugtask_product_fk FOREIGN KEY (product)
    REFERENCES product(id);
ALTER TABLE ONLY BugTask ADD CONSTRAINT bugtask_sourcepackagename_fk
    FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);
ALTER TABLE ONLY BugTask ADD CONSTRAINT bugtask_distribution_fk
    FOREIGN KEY (distribution) REFERENCES distribution(id);
ALTER TABLE ONLY BugTask ADD CONSTRAINT bugtask_distrorelease_fk
    FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);
ALTER TABLE ONLY BugTask
    ADD CONSTRAINT bugtask_binarypackagename_fk
    FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);
ALTER TABLE ONLY BugTask ADD CONSTRAINT bugtask_person_fk
    FOREIGN KEY (assignee) REFERENCES person(id);
ALTER TABLE ONLY BugTask
    ADD CONSTRAINT bugtask_owner_fk
    FOREIGN KEY ("owner") REFERENCES person(id);
    

/* Indexes */
CREATE INDEX bugtask_bug_idx ON BugTask(bug);
CREATE INDEX bugtask_product_idx ON BugTask(product);
CREATE INDEX bugtask_sourcepackagename_idx ON BugTask(sourcepackagename);
CREATE INDEX bugtask_distribution_idx ON BugTask(distribution);
CREATE INDEX bugtask_distrorelease_idx ON BugTask(distrorelease);
CREATE INDEX bugtask_binarypackagename_idx ON BugTask(binarypackagename);
CREATE INDEX bugtask_assignee_idx ON BugTask(assignee);
CREATE INDEX bugtask_owner_idx ON BugTask("owner");

/* schitzo table constraints */
ALTER TABLE ONLY BugTask ADD CONSTRAINT bugtask_assignment_checks
    CHECK (product IS NULL <> distribution IS NULL);

/* indexes */

UPDATE LaunchpadDatabaseRevision SET major=6,minor=11,patch=0;

