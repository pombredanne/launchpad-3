SET client_min_messages=ERROR;
/*
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
*/
BEGIN;

-- ProductReleases are only unique on the version and productseries,
-- which causes a problem when merging them with Milestones, which
-- are unique on the name and product.
ALTER TABLE Milestone
DROP CONSTRAINT milestone_name_product_key;

ALTER TABLE Milestone
ADD UNIQUE (name, productseries);

ALTER TABLE Milestone
ADD COLUMN codename TEXT;

-- Link milestones and releases with matching names and productseries.
UPDATE ProductRelease
SET milestone = Milestone.id
FROM Milestone
WHERE Milestone.name = lower(ProductRelease.version)
    AND Milestone.productseries = ProductRelease.productseries;

-- Append ProductRelease.description to Milestone.description.
UPDATE Milestone
SET codename = ProductRelease.codename,
    description = coalesce(Milestone.description, '')
                  || E'\n' || coalesce(ProductRelease.summary, '')
                  || E'\n' || coalesce(ProductRelease.description, '')
FROM ProductRelease
WHERE ProductRelease.milestone = Milestone.id;

-- Create new milestones for releases that don't match.
INSERT INTO Milestone (
    product,
    productseries,
    name,
    description,
    codename)
SELECT
    series.product,
    release.productseries,
    lower(release.version),
    coalesce(release.summary, '')
        || E'\n' || coalesce(release.description, ''),
    codename
FROM ProductRelease release
    JOIN ProductSeries series ON series.id = release.productseries
WHERE milestone IS NULL;

-- Link releases to the newly created milestones.
UPDATE ProductRelease
SET milestone = Milestone.id
FROM Milestone
WHERE Milestone.name = lower(ProductRelease.version)
    AND Milestone.productseries = ProductRelease.productseries
    AND (Milestone.description =
            coalesce(ProductRelease.summary, '')
                || E'\n' || coalesce(ProductRelease.description, '')
         OR (Milestone.description IS NULL
             AND ProductRelease.description IS NULL));

-- Add NOT NULL constraint.
ALTER TABLE ProductRelease
ALTER COLUMN milestone SET NOT NULL;

-- The version and productseries columns are going away, and there is no point
-- in ensuring that they are unique.
ALTER TABLE ProductRelease
DROP constraint productrelease_productseries_version_key;

ALTER TABLE ProductRelease
DROP COLUMN version;

ALTER TABLE ProductRelease
DROP COLUMN codename;

ALTER TABLE ProductRelease
DROP COLUMN summary;

ALTER TABLE ProductRelease
DROP COLUMN description;

ALTER TABLE ProductRelease
DROP COLUMN productseries;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
COMMIT;
