SET client_min_messages=ERROR;

-- Remove unsued columns
ALTER TABLE BinaryPackageRelease DROP COLUMN copyright;
ALTER TABLE BinaryPackageRelease DROP COLUMN licence;

-- Store copyright contents for each SourcePackageRelease.
ALTER TABLE SourcePackageRelease ADD COLUMN copyright TEXT;


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 27, 0);

