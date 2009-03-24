SET client_min_messages=ERROR;

-- The level of importing of translations for this series from a branch in 
-- codehosting. Could be "No import", "POT files only", "POT and PO files"

ALTER TABLE ProductSeries
  ADD COLUMN translations_autoimport_mode integer NOT NULL DEFAULT 1;

ALTER TABLE ProductSeries
    ADD CONSTRAINT productseries__product__name__key UNIQUE (product, name);
ALTER TABLE ProductSeries DROP CONSTRAINT productseries_product_key;
CLUSTER ProductSeries USING productseries__product__name__key;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 29, 0);

