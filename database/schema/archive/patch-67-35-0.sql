SET client_min_messages=ERROR;


-- New fields used in NoMoreAptFtparchive implementation
-- Ideally they should be NOT NULL (they are in content classes
-- and interfaces) however we need to migrate old data before
-- setting it.
ALTER TABLE SourcePackageRelease ADD COLUMN dsc_maintainer_rfc822 text;
ALTER TABLE SourcePackageRelease ADD COLUMN dsc_standards_version text;
ALTER TABLE SourcePackageRelease ADD COLUMN dsc_format text;
ALTER TABLE SourcePackageRelease ADD COLUMN dsc_binaries text;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 35, 0);

