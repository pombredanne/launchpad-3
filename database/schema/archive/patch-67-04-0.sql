SET client_min_messages=ERROR;

-- Drop obsolete indexes now to speed things up
DROP INDEX shippingrequest_one_outstanding_request_unique;
DROP INDEX shippingrequest_pending_approval_idx;
DROP INDEX shippingrequest_pending_shipment_idx;
DROP INDEX shippingrequest_daterequested_untriaged;

-- Create the new status column and populate it with data
ALTER TABLE ShippingRequest ADD COLUMN status integer;

UPDATE ShippingRequest SET status=0 -- PENDING
    WHERE approved IS NULL AND cancelled IS FALSE AND shipment IS NULL; 

UPDATE ShippingRequest SET status=1 -- APPROVED
    WHERE approved IS TRUE AND cancelled IS FALSE AND shipment IS NULL;

UPDATE ShippingRequest SET status=2 -- DENIED
    WHERE approved IS FALSE AND shipment IS NULL;

UPDATE ShippingRequest SET status=3 -- CANCELLED
    WHERE cancelled IS TRUE AND approved IS NOT FALSE AND shipment IS NULL;

UPDATE ShippingRequest SET status=4 -- SHIPPED
    WHERE shipment IS NOT NULL;

ALTER TABLE ShippingRequest ALTER COLUMN status SET NOT NULL;

-- Add some CHECK constraints to confirm our data remains sane
ALTER TABLE ShippingRequest ADD CONSTRAINT enforce_shipped_status
    CHECK (status != 4 OR shipment IS NOT NULL);

-- Drop the old boolean flags
ALTER TABLE ShippingRequest DROP COLUMN approved;
ALTER TABLE ShippingRequest DROP COLUMN cancelled;

CREATE OR REPLACE FUNCTION create_the_index() RETURNS boolean AS $$
    rv = plpy.execute("SELECT id FROM Person WHERE name='shipit-admins'")
    try:
        shipit_admins_id = rv[0]["id"]
        assert shipit_admins_id == 243601, 'Unexpected shipit-admins id'
    except IndexError:
        shipit_admins_id = 54 # Value in sampledata
    sql = """
        CREATE UNIQUE INDEX shippingrequest_one_outstanding_request_unique
        ON ShippingRequest(recipient)
        WHERE
            shipment IS NULL
            AND status NOT IN (%(cancelled)d, %(denied)d)
            AND recipient != %(shipit_admins_id)d
        """ % {'shipit_admins_id': shipit_admins_id, 'cancelled': 3,
               'denied': 2}
    plpy.execute(sql)
    return True
$$ LANGUAGE plpythonu;

SELECT create_the_index();

DROP FUNCTION create_the_index();

-- Indexes required for admin queries:
-- 'select unapproved requests'
CREATE INDEX ShippingRequest__daterequested__unapproved__idx
    ON ShippingRequest(daterequested) WHERE status=0;
-- 'select unshipped requests'
CREATE INDEX ShippingRequest__daterequested__approved__idx
    ON ShippingRequest(daterequested) WHERE status=1;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 04, 0);
