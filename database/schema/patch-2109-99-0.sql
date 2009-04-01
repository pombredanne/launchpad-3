SET client_min_messages=ERROR;

ALTER TABLE Branch
   ADD COLUMN owner_name TEXT,
   ADD COLUMN target_name TEXT,
   ADD COLUMN unique_name TEXT;

-- Now, unique_name should have an index as we sometimes search based
-- on unique name.

-- owner_name probably doesn't need an index as we'd normally be searing based
-- on the owner id, and that does have an index.

-- owner_name should be NOT NULL, so we should populate it and set it not null.

-- target_name will be NULL for junk branches, and should be populated based
-- on either the product name or the sourcepackage name.

-- unique name should also be NOT NULL as it should always have a value.

-- Here is a query that gets the unique name for every branch:
/*
SELECT '~' || owner.name || '/' || coalesce(product.name,
distribution.name || '/' || distroseries.name || '/' ||
sourcepackagename.name, '+junk') || '/' || branch.name
FROM branch
LEFT JOIN distroseries ON branch.distroseries = distroseries.id
LEFT JOIN product ON branch.product = product.id
LEFT JOIN distribution ON distroseries.distribution = distribution.id
LEFT JOIN sourcepackagename ON sourcepackagename.id = branch.sourcepackagename
JOIN person AS owner ON owner.id = branch.owner;
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
