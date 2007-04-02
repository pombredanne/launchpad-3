SET client_min_messages=ERROR;

CREATE INDEX shippingrequest__normalized_address__idx
    ON ShippingRequest(normalized_address);

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 18, 1);

