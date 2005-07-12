SET client_min_messages=ERROR;

ALTER TABLE GPGKey RENAME COLUMN revoked TO active;
UPDATE GPGKey SET active = NOT active;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 42, 0);

