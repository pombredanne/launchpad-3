
/*
  We need a few status flags on project / product to ensure that we get the chance
  to sanitise the data that gets created. For the moment these won't influence search
  results etc, but in time that may happen.
*/

ALTER TABLE Project ADD COLUMN reviewed boolean;
ALTER TABLE Project ALTER COLUMN reviewed SET DEFAULT False;
UPDATE Project SET reviewed = False WHERE reviewed IS NULL;
ALTER TABLE Project ALTER COLUMN reviewed SET NOT NULL;

COMMENT ON COLUMN Project.reviewed IS 'Whether or not someone at Canonical has reviewed this project.';


ALTER TABLE Project ADD COLUMN active boolean;
ALTER TABLE Project ALTER COLUMN active SET DEFAULT True;
UPDATE Project SET active = True WHERE active IS NULL;
ALTER TABLE Project ALTER COLUMN active SET NOT NULL;

COMMENT ON COLUMN Project.active IS 'Whether or not this project should be considered active.';


ALTER TABLE Product ADD COLUMN reviewed boolean;
ALTER TABLE Product ALTER COLUMN reviewed SET DEFAULT False;
UPDATE Product SET reviewed = False WHERE reviewed IS NULL;
ALTER TABLE Product ALTER COLUMN reviewed SET NOT NULL;

COMMENT ON COLUMN Product.reviewed IS 'Whether or not someone at Canonical has reviewed this product.';


ALTER TABLE Product ADD COLUMN active boolean;
ALTER TABLE Product ALTER COLUMN active SET DEFAULT True;
UPDATE Product SET active = True WHERE active IS NULL;
ALTER TABLE Product ALTER COLUMN active SET NOT NULL;

COMMENT ON COLUMN Product.active IS 'Whether or not this product should be considered active.';


