SET client_min_messages=ERROR;

-- The default value used here is the value of DistroSeriesStatus.DEVELOPMENT.
-- We plan to rename it to something more generic so that it can be shared
-- between ProductSeries and DistroSeries.
ALTER TABLE ProductSeries ADD COLUMN status INTEGER DEFAULT 2;
UPDATE ProductSeries SET status = 2;

ALTER TABLE ProductSeries ALTER COLUMN status SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 42, 0);
