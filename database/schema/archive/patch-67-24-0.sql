SET client_min_messages=ERROR;

ALTER TABLE DistributionMirror DROP COLUMN file_list;
ALTER TABLE DistributionMirror DROP COLUMN pulse_source;
ALTER TABLE DistributionMirror DROP COLUMN pulse_type;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 24, 0);

