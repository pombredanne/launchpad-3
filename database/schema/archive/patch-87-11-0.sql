SET client_min_messages=ERROR;

ALTER TABLE DistributionMirror ADD COLUMN whiteboard TEXT DEFAULT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 11, 0);

