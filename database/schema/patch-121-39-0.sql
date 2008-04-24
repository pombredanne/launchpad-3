SET client_min_messages=ERROR;

ALTER TABLE ShippingRequest DROP COLUMN shockandawe;

DROP TABLE shockandawe;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 39, 0);
