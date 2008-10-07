SET client_min_messages=ERROR;

ALTER TABLE PackageDiff ADD COLUMN status INTEGER;
ALTER TABLE PackageDiff ALTER COLUMN status SET NOT NULL;
ALTER TABLE PackageDiff ALTER COLUMN status SET DEFAULT 0;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
