set client_min_messages=ERROR;

ALTER TABLE ShippingRequest ADD CONSTRAINT printable_addresses CHECK (
    is_printable_ascii(
        COALESCE(recipientdisplayname, '') ||
        COALESCE(addressline1, '') ||
        COALESCE(addressline2, '') ||
        COALESCE(organization, '') ||
        COALESCE(city, '') ||
        COALESCE(province, '') ||
        COALESCE(postcode, '') ||
        COALESCE(phone, '')
        )
    );

CREATE INDEX shippingrequest_approved_cancelled_idx
    ON ShippingRequest(approved, cancelled);

CREATE INDEX shippingrequest_daterequested_idx
    ON ShippingRequest(daterequested);

CREATE INDEX shippingrequest_highpriority_idx
    ON ShippingRequest(highpriority);

-- Drop duplicate constraint
ALTER TABLE Shipment DROP CONSTRAINT shipment_logintoken_uniq;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 36, 0);

