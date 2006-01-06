SET client_min_messages=ERROR;

CREATE INDEX requestedcds_request_architecture_idx
    ON RequestedCDs(request, architecture);
CREATE INDEX shippingrequest_recipient_idx ON ShippingRequest(recipient);
-- This should probably be a UNIQUE constraint. Bug 2490
CREATE INDEX shippingrequest_shipment_idx ON ShippingRequest(shipment);
ALTER TABLE Shipment ADD CONSTRAINT shipment_logintoken_uniq UNIQUE(logintoken);
CREATE INDEX shipment_shippingrun_idx ON Shipment(shippingrun);

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 30, 0);

