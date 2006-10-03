SET client_min_messages=ERROR;

/* Fill in ProductSeries.releaseroot from Product.releaseroot and then
 * drop Product.releaseroot. */

UPDATE ProductSeries SET
  releaseroot = Product.releaseroot
  FROM Product
  WHERE Product.id = ProductSeries.product AND
    ProductSeries.releaseroot IS NULL;

ALTER TABLE Product DROP COLUMN releaseroot;

-- Trim leading and trailing whitespace from releaseroot and releasefileglob
UPDATE ProductSeries SET
  releaseroot = btrim(releaseroot),
  releasefileglob = btrim(releasefileglob);

-- NULL out releaseroot and releasefileglob if they are empty
UPDATE ProductSeries SET
  releaseroot = NULL WHERE releaseroot = '';
UPDATE ProductSeries SET
  releasefileglob = NULL WHERE releasefileglob = '';

-- Merge ProductSeries.releaseroot into ProductSeries.releasefileglob.
-- First make sure the releaseroot ends with a slash...
UPDATE ProductSeries SET
  releaseroot = releaseroot || '/'
  WHERE releaseroot IS NOT NULL AND releaseroot NOT LIKE '%/';

-- Then merge the fields
UPDATE ProductSeries SET
  releasefileglob = releaseroot || releasefileglob
  WHERE releasefileglob IS NOT NULL;

ALTER TABLE ProductSeries DROP COLUMN releaseroot;

-- The releasefileglob should be a valid absolute URL
ALTER TABLE ProductSeries
  ADD CONSTRAINT valid_releasefileglob
    CHECK (valid_absolute_url(releasefileglob));

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 23, 0);
