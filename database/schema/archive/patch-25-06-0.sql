SET client_min_messages = ERROR;

ALTER TABLE BinaryPackage DROP CONSTRAINT valid_version;
ALTER TABLE BinaryPackage ADD CONSTRAINT valid_version
    CHECK (valid_debian_version(version));

ALTER TABLE SourcePackageRelease DROP CONSTRAINT valid_version;
ALTER TABLE SourcePackageRelease ADD CONSTRAINT valid_version
    CHECK (valid_debian_version(version));

ALTER TABLE ProductRelease DROP CONSTRAINT valid_version;
ALTER TABLE ProductRelease ADD CONSTRAINT valid_version
    CHECK (sane_version(version));

ALTER TABLE DistroRelease DROP CONSTRAINT valid_version;
ALTER TABLE DistroRelease ADD CONSTRAINT valid_version
    CHECK (sane_version(version));

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 6, 0);

