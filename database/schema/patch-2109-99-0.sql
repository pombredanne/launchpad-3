SET client_min_messages=ERROR;

-- PackageUpload.changesfile is optional for accommodating
-- delayed-copies.
ALTER TABLE PackageUpload ALTER COLUMN changesfile DROP NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
