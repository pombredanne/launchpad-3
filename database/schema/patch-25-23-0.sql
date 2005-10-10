SET client_min_messages=ERROR;

UPDATE binarypackagerelease SET essential=FALSE WHERE essential IS NULL;
ALTER TABLE binarypackagerelease ALTER COLUMN essential SET NOT NULL;

UPDATE pofile SET rawfilepublished=FALSE 
    WHERE rawfilepublished IS NULL AND rawfile IS NOT NULL;


-- Move the priority column from the Shipment table to the ShippingRequest one.

ALTER TABLE Shipment DROP COLUMN priority;

ALTER TABLE ShippingRequest ADD COLUMN highpriority boolean;
UPDATE ShippingRequest SET highpriority = FALSE;
ALTER TABLE ShippingRequest ALTER COLUMN highpriority SET DEFAULT FALSE;
ALTER TABLE ShippingRequest ALTER COLUMN highpriority SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,23,0);
