-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;
/*
Migrate columns from ProductRelease to Milestone.
The migrated columns are indicated below, marked with a *

    Column     |            Type             |
---------------+-----------------------------+--------------------------------
 id            | integer                     | not null default nextval(
 datereleased  | timestamp without time zone | not null
*version       | text                        | not null
*codename      | text                        |
*description   | text                        |
 changelog     | text                        |
 owner         | integer                     | not null
*summary       | text                        |
*productseries | integer                     | not null
 datecreated   | timestamp without time zone | not null default timezone('UTC'
 milestone     | integer                     |


SUMMARY OF CHANGES:
    RENAME
        Milestone.description TO summary
        Milestone.visible TO active
        ProductRelease.description TO release_notes
    DELETE
        ProductRelease.summary (append to Milestone.summary)
        ProductRelease.version (same as Milestone.name)
        ProductRelease.codename (move to Milestone)
        ProductRelease.productseries
    ADD
        Milestone.codename
        NOTNULL constraint on ProductRelease.milestone
*/


-- ProductReleases are only unique on the version and productseries,
-- which causes a problem when merging them with Milestones, which
-- are unique on the name and product.
ALTER TABLE Milestone
ADD COLUMN codename TEXT;

ALTER TABLE Milestone
RENAME COLUMN description TO summary;

ALTER TABLE Milestone
RENAME COLUMN visible TO active;

ALTER TABLE ProductRelease
RENAME COLUMN description TO release_notes;

-- Link milestones and releases with matching names and productseries.
UPDATE ProductRelease
SET milestone = Milestone.id
FROM Milestone
WHERE Milestone.name = lower(ProductRelease.version)
    AND Milestone.productseries = ProductRelease.productseries;

-- Append ProductRelease.summary to Milestone.summary.
UPDATE Milestone
SET codename = ProductRelease.codename,
    summary = coalesce(Milestone.summary, '')
                  || E'\n' || coalesce(ProductRelease.summary, '')
FROM ProductRelease
WHERE ProductRelease.milestone = Milestone.id;

-- Create new milestones for releases that don't match.
INSERT INTO Milestone (
    product,
    productseries,
    name,
    summary,
    codename,
    active)
SELECT
    series.product,
    release.productseries,
    lower(release.version),
    coalesce(release.summary, ''),
    codename,
    FALSE
FROM ProductRelease release
    JOIN ProductSeries series ON series.id = release.productseries
WHERE milestone IS NULL;

-- Link releases to the newly created milestones.
UPDATE ProductRelease
SET milestone = Milestone.id
FROM Milestone
WHERE Milestone.name = lower(ProductRelease.version)
    AND Milestone.productseries = ProductRelease.productseries
    AND (Milestone.summary = coalesce(ProductRelease.summary, '')
         OR (Milestone.summary IS NULL
             AND ProductRelease.summary IS NULL));

-- Add NOT NULL constraint.
ALTER TABLE ProductRelease
ALTER COLUMN milestone SET NOT NULL;

ALTER TABLE ProductRelease
DROP COLUMN version;

ALTER TABLE ProductRelease
DROP COLUMN codename;

ALTER TABLE ProductRelease
DROP COLUMN summary;

ALTER TABLE ProductRelease
DROP COLUMN productseries;

-- Debloat
CLUSTER ProductRelease USING productrelease_pkey;
CLUSTER MileStone USING milestone_pkey;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 24, 0);
