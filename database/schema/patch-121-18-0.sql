SET client_min_messages=ERROR;

ALTER TABLE DistributionSourcePackageCache ALTER COLUMN archive SET NOT NULL;
ALTER TABLE DistroSeriesPackageCache ALTER COLUMN archive SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 18, 0);
