SET client_min_messages=ERROR;

ALTER TABLE ShippingRequest ADD COLUMN type integer;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 49, 0);

