SET client_min_messages=ERROR;

CREATE UNIQUE INDEX hwdevice__bus_vendor_id__bus_product_id__key
  ON hwdevice USING btree (bus_vendor_id, bus_product_id) WHERE variant IS NULL;

CREATE UNIQUE INDEX hwdriver__name__key ON hwdriver USING btree (name) 
  WHERE package_name IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
