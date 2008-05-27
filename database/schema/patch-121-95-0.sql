-- Fixes for database schema problems uncovered by Storm work.

SET client_min_messages=ERROR;

-- DistroSeriesPackageCache.id's default used a non-existent sequence
ALTER TABLE DistroSeriesPackageCache
  ALTER COLUMN id SET DEFAULT nextval('distroseriespackagecache_id_seq');

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 95, 0);
