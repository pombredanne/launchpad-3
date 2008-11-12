SET client_min_messages=ERROR;

-- Link milestones and releases with matching names and productseries.
UPDATE ProductRelease
SET milestone = Milestone.id
FROM Milestone
WHERE Milestone.name = lower(ProductRelease.version)
    AND Milestone.productseries = ProductRelease.productseries
    AND Milestone.description = ProductRelease.description;

-- Append ProductRelease.description to Milestone.description.
UPDATE Milestone
SET description = coalesce(Milestone.description, '')
                  || E'\n' || coalesce(ProductRelease.description, '')
FROM ProductRelease
WHERE ProductRelease.milestone = Milestone.id;

-- Create new milestones for releases that don't match.
INSERT INTO Milestone (product, productseries, name, description)
SELECT
    series.product,
    release.productseries,
    lower(release.version),
    release.description
FROM ProductRelease release
    JOIN ProductSeries series ON series.id = release.productseries
WHERE milestone IS NULL;

-- Link releases to the newly created milestones.
UPDATE ProductRelease
SET milestone = Milestone.id
FROM Milestone
WHERE Milestone.name = lower(ProductRelease.version)
    AND Milestone.productseries = ProductRelease.productseries
    AND (Milestone.description = ProductRelease.description
         OR (Milestone.description IS NULL
             AND ProductRelease.description IS NULL));

-- Add NOT NULL constraint.
ALTER TABLE ProductRelease
ALTER COLUMN milestone SET NOT NULL;

-- The version and productseries columns are going away, and there is no point
-- in ensuring that they are unique.
ALTER TABLE productrelease
DROP constraint productrelease_productseries_version_key;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 8, 99);
