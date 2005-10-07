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

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 36, 0);

