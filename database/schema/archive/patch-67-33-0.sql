SET client_min_messages=ERROR;

ALTER TABLE PillarName
    ADD COLUMN active boolean DEFAULT TRUE NOT NULL;

UPDATE PillarName SET active=FALSE
FROM Product
WHERE PillarName.product = Product.id
    AND Product.active = FALSE;

UPDATE PillarName SET active=FALSE
FROM Project
WHERE PillarName.project = Project.id
    AND Project.active = FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 33, 0);
