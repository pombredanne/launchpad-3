SET client_min_messages=ERROR;

UPDATE DistributionMirror SET speed = (10 * speed);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 36, 0);
