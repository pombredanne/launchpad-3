SET client_min_messages = ERROR;

ALTER TABLE ShippingRun ADD COLUMN requests_count integer NOT NULL DEFAULT 0;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 18, 0);
