SET client_min_messages = ERROR;

ALTER TABLE ShippingRun ADD COLUMN requests_count integer;

UPDATE ShippingRun SET requests_count = (
    SELECT count(*) FROM Shipment WHERE Shipment.shippingrun = ShippingRun.id
    );

ALTER TABLE ShippingRun ALTER COLUMN requests_count SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 15, 0);
