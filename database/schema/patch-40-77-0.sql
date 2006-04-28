SET client_min_messages=ERROR;

ALTER TABLE StandardShipItRequest ADD COLUMN flavour integer;
ALTER TABLE StandardShipItRequest DROP COLUMN description;

ALTER TABLE StandardShipItRequest 
    DROP CONSTRAINT standardshipitrequest_quantityx86_key;

ALTER TABLE standardshipitrequest
    ADD CONSTRAINT standardshipitrequest_quantity_flavour_key 
    UNIQUE (flavour, quantityx86, quantityppc, quantityamd64);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 77, 0);

