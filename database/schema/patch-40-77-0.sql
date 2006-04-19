SET client_min_messages=ERROR;

-- XXX: This patch will require lots of data migration!

--ALTER TABLE ShippingRequest DROP COLUMN approved;
--ALTER TABLE ShippingRequest DROP COLUMN whoapproved;

--ALTER TABLE RequestedCDs DROP COLUMN quantityapproved;

ALTER TABLE RequestedCDs ALTER COLUMN quantityapproved SET NOT NULL;

ALTER TABLE StandardShipItRequest ADD COLUMN flavour integer;
ALTER TABLE StandardShipItRequest DROP COLUMN description;

ALTER TABLE StandardShipItRequest 
    DROP CONSTRAINT standardshipitrequest_quantityx86_key;

ALTER TABLE standardshipitrequest
    ADD CONSTRAINT standardshipitrequest_quantity_flavour_key 
    UNIQUE (flavour, quantityx86, quantityppc, quantityamd64);

-- All existing standard requests are for the Ubuntu flavour.
-- XXX: I think this needs to be moved to a migration script.
UPDATE StandardShipItRequest SET flavour = 1;

ALTER TABLE StandardShipItRequest ALTER COLUMN flavour SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 77, 0);

