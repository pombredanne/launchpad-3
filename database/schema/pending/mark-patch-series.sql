SET client_min_messages TO error;

/*
  - Give each Series a shortdesc as well.
  - Allow a ProductReleast to be in a Series
*/

ALTER TABLE ProductSeries ADD COLUMN shortdesc TEXT;
ALTER TABLE ProductSeries ALTER COLUMN shortdesc SET NOT NULL;

COMMENT ON COLUMN ProductSeries.shortdesc IS 'A short description of this Product Series. A good example would include the date the series was initiated and whether this is the current recommended series for people to use.';

ALTER TABLE ProductRelease ADD COLUMN productseries INT REFERENCES ProductSeries;

COMMENT ON COLUMN ProductRelease.productseries IS 'A pointer to the Product Series this release forms part of. Using a Product Series allows us to distinguish between releases on stable and development branches of a product even if they are interspersed in time.';
