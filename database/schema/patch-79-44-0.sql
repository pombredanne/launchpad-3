SET client_min_messages=ERROR;

-- This new column is maintained by a trigger because it's safer than hacking
-- sqlobject's internals. Specially because we sometimes update data behind
-- sqlobject's back.
ALTER TABLE ShippingRequest ADD COLUMN normalized_address text;
CREATE TRIGGER set_normalized_address
    BEFORE INSERT OR UPDATE ON ShippingRequest
    FOR EACH ROW
    EXECUTE PROCEDURE set_shipit_normalized_address();

-- XXX: How can I fire the above trigger for all existing rows?

ALTER TABLE ShippingRequest ALTER COLUMN normalized_address SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 44, 0);
