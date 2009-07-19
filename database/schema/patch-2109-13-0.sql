-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Source package branches!

-- Refer to a source package with the pair (DistroSeries, SourcePackageName)
ALTER TABLE Branch
    ADD COLUMN distroseries int REFERENCES DistroSeries(id),
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
-- Redundant? Drop next cycle - need to confirm not used for weird joins.
-- DROP INDEX branch__product__id__idx;

CREATE UNIQUE INDEX branch__product__owner__name__key
    ON Branch(product, owner, name)
    WHERE product IS NOT NULL;

CREATE UNIQUE INDEX branch__owner__name__key
    ON Branch(owner, name)
    WHERE product IS NULL AND distroseries IS NULL;

-- Also used for foreign key lookups when modifying DistroSeries
CREATE UNIQUE INDEX branch__ds__spn__owner__name__key
    ON Branch(distroseries, sourcepackagename, owner, name)
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
    CONSTRAINT branchsourcepackageseries__ds__spn__pocket__branch__key
        UNIQUE (distroseries, sourcepackagename, pocket, branch)
);

CREATE INDEX seriessourcepackagebranch__branch__idx
    ON SeriesSourcePackageBranch(branch);

-- For person merge.
CREATE INDEX seriessourcepackagebranch__registrant__key
    ON SeriesSourcePackageBranch(registrant);


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 13, 0);
