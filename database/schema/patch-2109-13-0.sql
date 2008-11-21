SET client_min_messages=ERROR;

-- Source package branches!

-- Refer to a source package with the pair (DistroSeries, SourcePackageName)
ALTER TABLE Branch
    ADD COLUMN distroseries int REFERENCES DistroSeries(id);

ALTER TABLE Branch
    ADD COLUMN sourcepackagename int REFERENCES SourcePackageName(id);

-- A Branch can either be a product branch, a personal branch (i.e. +junk) or
-- a source package branch

-- Constrain one of:
--   - distroseries == sourcepackagename == product == NULL
--   - distroseries, sourcepackagename NOT NULL; product NULL
--   - distroseries, sourcepackagename NULL; product NOT NULL
--
-- A Branch can either be a product branch, a personal branch (i.e. +junk) or
-- a source package branch
--
-- ~jml/+junk/dot-emacs
-- ~jml/testtools/trunk
-- ~jml/ubuntu/testtools/trunk

ALTER TABLE Branch
    ADD CONSTRAINT one_container CHECK (
        ((distroseries IS NULL) = (sourcepackagename IS NULL))
         AND ((distroseries IS NULL) OR (product IS NULL)));


-- Remove the uniqueness constraint on (owner, product, name) and
-- replace it so that:
--     - (owner, product, distroseries, sourcepackagename, name) is unique
--     - (owner, product, name) and (owner, distribution, sourcepackagename, name)
--       are easy to search for.

DROP INDEX branch_name_owner_product_key;

CREATE UNIQUE INDEX branch_name_owner_product_key
    ON Branch(name, owner, (COALESCE(product, (-1))))
    WHERE distroseries IS NULL;


-- I guess we need to index:
--     - this pair
--     - the "unique name": owner, distribution, sourcepackagename, name

CREATE UNIQUE INDEX branch__distroseries__sourcepackagename__key
    ON Branch(name, owner, distroseries, sourcepackagename)
    WHERE distroseries IS NOT NULL;


-- Link /ubuntu/<suite>/<package> to a branch.
CREATE TABLE SeriesSourcePackageBranch (
    id serial PRIMARY KEY,
    distroseries integer NOT NULL REFERENCES DistroSeries(id),
    pocket integer NOT NULL,
    sourcepackagename int NOT NULL REFERENCES SourcePackageName(id),
    branch integer NOT NULL REFERENCES Branch(id),
    registrant integer NOT NULL REFERENCES Person(id),
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    CONSTRAINT branchsourcepackageseries__branch__distroseries__pocket__key
        UNIQUE (branch, distroseries, pocket, sourcepackagename)
);

CREATE INDEX seriessourcepackagebranch__branch
    ON SeriesSourcePackageBranch(branch);

-- For person merge.
CREATE INDEX seriessourcepackagebranch__registrant__key
    ON SeriesSourcePackageBranch(registrant);


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 13, 0);
