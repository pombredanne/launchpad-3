SET client_min_messages=ERROR;

/* We need to enforce a single outstanding request per recipient. We
can't maintain multi table constraints without race conditions, so we need
to duplicate the information that a shipment exists in the shippingrequest
table */

ALTER TABLE ShippingRequest ADD COLUMN shipped boolean NOT NULL DEFAULT FALSE;

UPDATE ShippingRequest SET shipped=TRUE WHERE id IN (
    SELECT request FROM shipment);

CREATE TRIGGER shipment_maintain_shipped_flag_t
BEFORE INSERT OR UPDATE OR DELETE ON Shipment
FOR EACH ROW EXECUTE PROCEDURE shipment_maintain_shipped_flag();

/* This should be NOT NULL */
ALTER TABLE Shipment ALTER COLUMN request SET NOT NULL;

/* Trash orders that will violate our constraint. We leave the first unshipped
duplicate order untouched. */
DELETE FROM RequestedCDs
USING ShippingRequest
WHERE
    RequestedCDs.request = ShippingRequest.id
    AND shipped IS FALSE
    AND approved IS NOT FALSE
    AND cancelled IS FALSE
    AND recipient IN (
        SELECT recipient FROM ShippingRequest
        WHERE
            shipped IS FALSE
            AND approved IS NOT FALSE
            AND cancelled IS FALSE
        GROUP BY recipient
        HAVING count(*) > 1
        )
    AND ShippingRequest.id NOT IN (
        SELECT min(id)
        FROM ShippingRequest
        WHERE
            shipped IS FALSE
            AND approved IS NOT FALSE
            AND cancelled IS FALSE
        GROUP BY recipient
        HAVING COUNT(*) > 1
        );

DELETE FROM ShippingRequest
WHERE
    shipped IS FALSE
    AND recipient IN (
        SELECT recipient FROM ShippingRequest
        WHERE
            shipped IS FALSE
            AND approved IS NOT FALSE
            AND cancelled IS FALSE
        GROUP BY recipient
        HAVING count(*) > 1
        )
    AND id NOT IN (
        SELECT min(id)
        FROM ShippingRequest
        WHERE
            shipped IS FALSE
            AND approved IS NOT FALSE
            AND cancelled IS FALSE
        GROUP BY recipient
        HAVING COUNT(*) > 1
        );

CREATE OR REPLACE FUNCTION create_the_index() RETURNS boolean AS $$
    rv = plpy.execute("SELECT id FROM Person WHERE name='shipit-admins'")
    try:
        shipit_admins_id = rv[0]["id"]
        assert shipit_admins_id == 243601, 'Unexpected shipit-admins id'
    except IndexError:
        shipit_admins_id = 54 # Value in sampledata
    sql = """
        /* Now create the constraint */
        CREATE UNIQUE INDEX shippingrequest_one_outstanding_request_unique
        ON ShippingRequest(recipient)
        WHERE
            shipped IS FALSE
            AND cancelled IS FALSE
            AND approved IS NOT FALSE
            AND recipient != %d
        """ % shipit_admins_id
    plpy.execute(sql)
    return True
$$ LANGUAGE plpythonu;

SELECT create_the_index();

DROP FUNCTION create_the_index();

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 59, 0);

