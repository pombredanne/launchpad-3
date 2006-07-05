SET client_min_messages=ERROR;

ALTER TABLE StandardShipItRequest ADD COLUMN flavour integer;
ALTER TABLE StandardShipItRequest DROP COLUMN description;

ALTER TABLE StandardShipItRequest
    DROP CONSTRAINT standardshipitrequest_quantityx86_key;

UPDATE RequestedCDs SET quantityapproved = 0 WHERE quantityapproved IS NULL;
ALTER TABLE RequestedCDs ALTER COLUMN quantityapproved SET NOT NULL;

-- All existing standard requests are for the Ubuntu flavour.
UPDATE StandardShipItRequest SET flavour = 1 WHERE flavour IS NULL;
ALTER TABLE StandardShipItRequest ALTER COLUMN flavour SET NOT NULL;

ALTER TABLE standardshipitrequest
ADD CONSTRAINT standardshipitrequest_flavour_quantity_key
    UNIQUE (flavour, quantityx86, quantityppc, quantityamd64);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 55, 0);

