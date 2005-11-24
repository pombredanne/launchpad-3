SET client_min_messages=ERROR;

ALTER TABLE ShippingRequest DROP COLUMN shipment;
ALTER TABLE ShippingRequest ALTER COLUMN country SET NOT NULL;
ALTER TABLE ShippingRequest ALTER COLUMN city SET NOT NULL;
ALTER TABLE ShippingRequest ALTER COLUMN addressline1 SET NOT NULL;
ALTER TABLE ShippingRequest ALTER COLUMN recipientdisplayname SET NOT NULL;

ALTER TABLE Shipment ALTER COLUMN dateshipped DROP NOT NULL;
ALTER TABLE Shipment ALTER COLUMN logintoken SET NOT NULL;
ALTER TABLE Shipment ADD COLUMN request integer;
ALTER TABLE Shipment ADD CONSTRAINT shipment_request_uniq UNIQUE(request);
ALTER TABLE Shipment ADD CONSTRAINT shipment_request_fk
                            FOREIGN KEY (request)
                            REFERENCES ShippingRequest(id);

ALTER TABLE ShippingRun ADD COLUMN sentforshipping boolean;
ALTER TABLE ShippingRun ALTER COLUMN sentforshipping SET DEFAULT FALSE;
ALTER TABLE ShippingRun ALTER COLUMN sentforshipping SET NOT NULL;

ALTER TABLE ShippingRun ADD COLUMN csvfile integer;

ALTER TABLE ShippingRun ADD CONSTRAINT shippingrun_csvfile_uniq UNIQUE(csvfile);

ALTER TABLE ShippingRun ADD CONSTRAINT shippingrun_csvfile_fk
                            FOREIGN KEY (csvfile)
                            REFERENCES LibraryFileAlias(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 34, 1);
