set client_min_messages=ERROR;

ALTER TABLE ShippingRequest ADD COLUMN recipientdisplayname text;
ALTER TABLE ShippingRequest ADD COLUMN addressline1 text;
ALTER TABLE ShippingRequest ADD COLUMN addressline2 text;
ALTER TABLE ShippingRequest ADD COLUMN organization text;
ALTER TABLE ShippingRequest ADD COLUMN city text;
ALTER TABLE ShippingRequest ADD COLUMN province text;
ALTER TABLE ShippingRequest ADD COLUMN country integer REFERENCES Country (id);
ALTER TABLE ShippingRequest ADD COLUMN postcode text;
ALTER TABLE ShippingRequest ADD COLUMN phone text;

UPDATE ShippingRequest
    SET addressline1 = Person.addressline1,
        addressline2 = Person.addressline2,
        organization = Person.organization,
        city = Person.city,
        province = Person.province,
        postcode = Person.postcode,
        country = Person.country,
        phone = Person.phone
    FROM Person
    WHERE ShippingRequest.recipient = Person.id;

ALTER TABLE ShippingRequest ADD CONSTRAINT 
    shippingrequest_shockandawe_fk FOREIGN KEY (shockandawe) 
    REFERENCES ShockAndAwe(id);

ALTER TABLE Shipment ADD CONSTRAINT 
    shipment_shippingrun_fk FOREIGN KEY (shippingrun) 
    REFERENCES ShippingRun(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (25,31,0);
