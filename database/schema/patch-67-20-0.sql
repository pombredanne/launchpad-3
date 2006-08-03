SET client_min_messages=ERROR;

-- Add a new column to the BugTask table for attaching bugs to productseries.
ALTER TABLE BugTask ADD COLUMN productseries INTEGER;
ALTER TABLE BugTask
    ADD CONSTRAINT bugtask_productseries_fk FOREIGN KEY (productseries) REFERENCES ProductSeries(id);
CREATE INDEX "bugtask_productseries_idx" ON BugTask(productseries);

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
        ELSE NULL
    END);

CREATE TABLE BugNomination (
    id serial PRIMARY KEY,
    bug integer NOT NULL,
    distrorelease integer,
    productseries integer,
    status integer NOT NULL,
    datecreated timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    "owner" integer NOT NULL
);

ALTER TABLE ONLY BugNomination ADD CONSTRAINT bugnomination_bug_fk
    FOREIGN KEY (bug) REFERENCES bug(id);
ALTER TABLE ONLY BugNomination ADD CONSTRAINT bugnomination_distrorelease_fk
    FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);
ALTER TABLE ONLY BugNomination ADD CONSTRAINT bugnomination_productseries_fk
    FOREIGN KEY (productseries) REFERENCES productseries(id);
ALTER TABLE ONLY BugNomination ADD CONSTRAINT bugnomination_owner_fk
    FOREIGN KEY ("owner") REFERENCES person(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 20, 0);