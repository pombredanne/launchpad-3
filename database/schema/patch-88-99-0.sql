SET client_min_messages=ERROR;

-- Creating new columns to store missing control-fields required in the
-- archive index. See bug #172308 for further information about this issue.

-- SourcePackageRelease.
ALTER TABLE SourcePackageRelease ADD COLUMN build_conflicts text;
ALTER TABLE SourcePackageRelease ADD COLUMN build_conflicts_indep text;

-- BinaryPackageRelease.
ALTER TABLE BinaryPackageRelease ADD COLUMN pre_depends text;
ALTER TABLE BinaryPackageRelease ADD COLUMN enhances text;
ALTER TABLE BinaryPackageRelease ADD COLUMN breaks text;


INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
