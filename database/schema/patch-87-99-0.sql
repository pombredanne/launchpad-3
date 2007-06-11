SET client_min_messages=ERROR;

ALTER TABLE Product ADD COLUMN private_bugs bool NOT NULL DEFAULT false;

COMMENT ON COLUMN product.private_bugs IS 'Indicates whether bugs filed in this product are automatically marked as private';

INSERT INTO LaunchPadDatabaseRevision VALUES(87,99,0);
