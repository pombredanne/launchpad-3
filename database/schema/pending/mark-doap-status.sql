
/*
  We need a few status flags on project / product to ensure that we get the chance
  to sanitise the data that gets created. For the moment these won't influence search
  results etc, but in time that may happen.
*/

ALTER TABLE Project ADD COLUMN status integer;
ALTER TABLE Project ALTER COLUMN status SET DEFAULT 1;
UPDATE Project SET status = DEFAULT WHERE status IS NULL;
ALTER TABLE Project ALTER COLUMN status SET NOT NULL;

COMMENT ON COLUMN Project.status IS 'An indicator of the status of the Project, see dbschema.ProjectStatus';


ALTER TABLE Product ADD COLUMN status integer;
ALTER TABLE Product ALTER COLUMN status SET DEFAULT 1;
UPDATE Product SET status = DEFAULT WHERE status IS NULL;
ALTER TABLE Product ALTER COLUMN status SET NOT NULL;

COMMENT ON COLUMN Product.status IS 'An indicator of the status of the Product, see dbschema.ProductStatus';


