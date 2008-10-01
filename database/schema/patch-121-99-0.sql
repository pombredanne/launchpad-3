SET client_min_messages=ERROR;

-- Source package branches!

-- Refer to a source package with the pair (Distribution, SourcePackageName)
ALTER TABLE Branch
    ADD COLUMN distribution int REFERENCES Distribution(id);

ALTER TABLE Branch
    ADD COLUMN sourcepackagename int REFERENCES SourcePackageName(id);

-- Constrain one of:
--   - distribution == sourcepackagename == product == NULL
--   - distribution, sourcepackagename NOT NULL; product NULL
--   - distribution, sourcepackagename NULL; product NOT NULL
--
-- A Branch can either be a product branch, a personal branch (i.e. +junk) or
-- a source package branch
--
-- ~jml/+junk/dot-emacs
-- ~jml/testtools/trunk
-- ~jml/ubuntu/testtools/trunk

ALTER TABLE Branch
    ADD CONSTRAINT one_container CHECK
        ((distribution IS NULL) = (sourcepackagename IS NULL))
         AND (distribution IS NULL) OR (product IS NULL);


-- I guess we need to index:
--     - this pair
--     - the "unique name": owner, distribution, sourcepackagename, name

CREATE INDEX branch__distribution__sourcepackagename
    ON Branch(distribution, sourcepackagename)
    WHERE distribution IS NOT NULL;


-- Remove the uniqueness constraint on (owner, product, name) and
-- replace it so that:
--     - (owner, product, distribution, sourcepackagename, name) is unique
--     - (owner, product, name) and (owner, distribution, sourcepackagename, name)
--       are easy to search for.

DROP INDEX branch_name_owner_product_key;

CREATE UNIQUE INDEX branch_name_owner_product_key
    ON Branch(name, owner, (COALESCE(product, (-1))))
    WHERE distribution IS NULL;


CREATE UNIQUE INDEX branch__distribution__sourcepackagename__key
    ON Branch(name, owner, distribution, sourcepackagename)
    WHERE distribution IS NOT NULL;


-- Link a source package branch to /ubuntu/<suite>/<package>.
CREATE TABLE BranchSourcePackageSeries (
    id serial PRIMARY KEY,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    registrant integer NOT NULL REFERENCES Person(id),
    branch integer NOT NULL REFERENCES Branch(id),
    distroseries integer NOT NULL REFERENCES DistroSeries(id),
    sourcepackagename integer NOT NULL REFERENCES SourcePackageName(id),
    pocket integer,
    CONSTRAINT branchsourcepackageseries__branch__distroseries__sourcepackagename__pocket__key
        UNIQUE (branch, distroseries, sourcepackagename, pocket)
);


CREATE INDEX branchsourcepackageseries__branch
    ON BranchSourcePackageSeries(branch);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
