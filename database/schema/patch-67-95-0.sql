SET client_min_messages=ERROR;

UPDATE ProductSeries SET rcstype = 0 WHERE rcstype IS NULL;

ALTER TABLE ProductSeries ALTER COLUMN rcstype SET NOT NULL;
ALTER TABLE ProductSeries ALTER COLUMN rcstype SET DEFAULT 0;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 95, 0);
