SET client_min_messages=ERROR;

/* Set a default on the ShippingRequest.daterequested column */
ALTER TABLE ShippingRequest ALTER COLUMN daterequested
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';

/* We need to enforce a single outstanding request per recipient. We
can't maintain multi table constraints without race conditions. So we
move Shipment.request to ShippingRequest.shipment
*/

ALTER TABLE ShippingRequest ADD COLUMN shipment integer;

UPDATE ShippingRequest
SET shipment = Shipment.id
FROM Shipment
WHERE Shipment.request = ShippingRequest.id;

ALTER TABLE ShippingRequest
    ADD CONSTRAINT shippingrequest_shipment_key UNIQUE (shipment);
ALTER TABLE ShippingRequest
    ADD CONSTRAINT shippingrequest_shipment_fk
    FOREIGN KEY (shipment) REFERENCES Shipment;

ALTER TABLE Shipment DROP COLUMN request;

/* Make shipit-admins the recipient of all outstanding orders whose recipient
is a shipit-admin. Note we use direct membership rather than the
TeamParticipation table so we don't screw with launchpad-administrator's
orders
*/
UPDATE ShippingRequest
SET recipient = (SELECT id FROM Person WHERE name='shipit-admins')
FROM Person, TeamMembership
WHERE recipient = TeamMembership.person
    AND TeamMembership.person = Person.id
    AND TeamMembership.team = (SELECT id FROM Person WHERE name='shipit-admins')
    AND cancelled IS FALSE
    AND approved IS NOT FALSE
    AND shipment IS NULL;

/* Trash orders that will violate our constraint. We leave the first unshipped
duplicate order untouched. */
DELETE FROM RequestedCDs
USING ShippingRequest
WHERE
    RequestedCDs.request = ShippingRequest.id
    AND shipment IS NULL
    AND approved IS NOT FALSE
    AND cancelled IS FALSE
    AND recipient <> (SELECT id FROM Person WHERE name='shipit-admins')
    AND recipient IN (
        SELECT recipient FROM ShippingRequest
        WHERE
            shipment IS NULL
            AND approved IS NOT FALSE
            AND cancelled IS FALSE
        GROUP BY recipient
        HAVING count(*) > 1
        )
    AND ShippingRequest.id NOT IN (
        SELECT min(id)
        FROM ShippingRequest
        WHERE
            shipment IS NULL
            AND approved IS NOT FALSE
            AND cancelled IS FALSE
        GROUP BY recipient
        HAVING COUNT(*) > 1
        );

DELETE FROM ShippingRequest
WHERE
    shipment IS NULL
    AND approved IS NOT FALSE
    AND cancelled IS FALSE
    AND recipient <> (SELECT id FROM Person WHERE name='shipit-admins')
    AND recipient IN (
        SELECT recipient FROM ShippingRequest
        WHERE
            shipment IS NULL
            AND approved IS NOT FALSE
            AND cancelled IS FALSE
        GROUP BY recipient
        HAVING count(*) > 1
        )
    AND id NOT IN (
        SELECT min(id)
        FROM ShippingRequest
        WHERE
            shipment IS NULL
            AND approved IS NOT FALSE
            AND cancelled IS FALSE
        GROUP BY recipient
        HAVING COUNT(*) > 1
        );

/* Now create the constraint. We do this using a stored procedure
   as we need to detect if we are running on production, or will be
   loading our sample data. This is because it is necessary for us to
   hard code the id of the shipit-admins team into the constraint.
 */
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
            AND cancelled IS FALSE
            AND approved IS NOT FALSE
            AND recipient != %d
        """ % shipit_admins_id
    plpy.execute(sql)
    return True
$$ LANGUAGE plpythonu;

SELECT create_the_index();

DROP FUNCTION create_the_index();

-- Remove unused indexes
DROP INDEX shippingrequest_cancelled_idx;
DROP INDEX shippingrequest_approved_cancelled_idx;

-- Remove bloat since cancelling is rare
DROP INDEX shippingrequest_whocancelled_idx;
CREATE INDEX shippingrequest__whocancelled__idx ON ShippingRequest(whocancelled)
    WHERE whocancelled IS NOT NULL;

-- Optimize admin queries for 'select unapproved requests'
CREATE UNIQUE INDEX ShippingRequest_pending_approval_idx
    ON ShippingRequest(id)
    WHERE shipment IS NULL AND cancelled IS FALSE AND approved IS NULL;

-- Optimize admin queries for 'select unshipped requests'
CREATE UNIQUE INDEX ShippingRequest_pending_shipment_idx
    ON ShippingRequest(id)
    WHERE shipment IS NULL AND cancelled IS FALSE AND approved IS TRUE;

-- These indexes are needed for people merge performance
CREATE INDEX product__security_contact__idx ON Product(security_contact)
    WHERE security_contact IS NOT NULL;
CREATE INDEX product__bugcontact__idx ON Product(bugcontact)
    WHERE bugcontact IS NOT NULL;
CREATE INDEX product__driver__idx ON Product(driver)
    WHERE driver IS NOT NULL;

-- Rename a constraint
ALTER TABLE ShippingRequest DROP CONSTRAINT "$1";
ALTER TABLE ShippingRequest ADD CONSTRAINT shippingrequest__country__fk
    FOREIGN KEY (country) REFERENCES Country;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 01, 0);

