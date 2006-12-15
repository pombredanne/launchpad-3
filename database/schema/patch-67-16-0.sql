SET client_min_messages=ERROR;

-- Add a new column to the BugTask table for attaching bugs to productseries.
ALTER TABLE BugTask ADD COLUMN productseries INTEGER;
ALTER TABLE BugTask
    ADD CONSTRAINT bugtask_productseries_fk
    FOREIGN KEY (productseries) REFERENCES ProductSeries(id);
CREATE INDEX bugtask__productseries__idx ON BugTask(productseries)
    WHERE productseries IS NOT NULL;

-- Ensure that only one of product, productseries, distribution, or
-- distrorelease are set. sourcepackagename can only be set on distribution or
-- distrorelease.
ALTER TABLE BugTask DROP CONSTRAINT bugtask_assignment_checks;
ALTER TABLE BugTask ADD CONSTRAINT bugtask_assignment_checks CHECK (
    CASE
        WHEN product IS NOT NULL THEN
            productseries IS NULL AND
            distribution IS NULL AND
            distrorelease IS NULL AND
            sourcepackagename IS NULL
        WHEN productseries IS NOT NULL THEN
            distribution IS NULL AND
            distrorelease IS NULL AND
            sourcepackagename IS NULL
        WHEN distribution IS NOT NULL THEN
            distrorelease IS NULL
        WHEN distrorelease IS NOT NULL THEN
            TRUE
        ELSE FALSE
    END);

DROP INDEX bugtask_distinct_sourcepackage_assignment;
CREATE UNIQUE INDEX bugtask_distinct_sourcepackage_assignment ON bugtask (
    bug,
    (COALESCE(sourcepackagename, -1)),
    (COALESCE(distrorelease, -1)),
    (COALESCE(distribution, -1))
    )
WHERE (product IS NULL AND productseries IS NULL);


CREATE TABLE BugNomination (
    id serial PRIMARY KEY,
    bug integer NOT NULL
        CONSTRAINT bugnomination__bug__fk REFERENCES Bug,
    distrorelease integer
        CONSTRAINT bugnomination__distrorelease__fk REFERENCES DistroRelease,
    productseries integer
        CONSTRAINT bugnomination__productseries__fk REFERENCES ProductSeries,
    status integer NOT NULL,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    date_decided timestamp without time zone,
    "owner" integer NOT NULL
        CONSTRAINT bugnomination__owner__fk REFERENCES Person,
    decider integer
        CONSTRAINT bugnomination__decider__fk REFERENCES Person
);

-- All foreign key references to the Person table need indexes so
-- people merge can operate efficiently
CREATE INDEX bugnomination__owner__idx ON BugNomination(owner);
CREATE INDEX bugnomination__decider__idx ON BugNomination(decider)
    WHERE decider IS NOT NULL;

-- Need to look up bugnominations by bug id
CREATE INDEX bugnomination__bug__idx ON BugNomination(bug);


INSERT INTO LaunchpadDatabaseRevision VALUES (67, 16, 0);