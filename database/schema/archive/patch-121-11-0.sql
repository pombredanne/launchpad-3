SET client_min_messages=ERROR;

ALTER TABLE HWDriver DROP CONSTRAINT hwdriver_license_fkey;

ALTER TABLE POTemplate DROP COLUMN license;

ALTER TABLE POFile DROP COLUMN license;

DROP TABLE License;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 11, 0);
