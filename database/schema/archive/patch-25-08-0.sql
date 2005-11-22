
set client_min_messages=ERROR;

ALTER TABLE SourcePackageRelease ADD CONSTRAINT
    sourcepackagerelease_manifest_uniq UNIQUE (manifest);

ALTER TABLE DistroArchRelease ADD CONSTRAINT
    distroarchrelease_distrorelease_architecturetag_unique UNIQUE
    (distrorelease, architecturetag);

ALTER TABLE DistroArchRelease ADD CONSTRAINT
    distroarchrelease_distrorelease_processorfamily_unique UNIQUE
    (distrorelease, processorfamily);

UPDATE PocketChroot SET pocket=20 WHERE pocket=1;
UPDATE PocketChroot SET pocket=10 WHERE pocket=2;

UPDATE SourcePackagePublishingHistory SET pocket=20 WHERE pocket=1;
UPDATE SourcePackagePublishingHistory SET pocket=10 WHERE pocket=2;

UPDATE PackagePublishingHistory SET pocket=20 WHERE pocket=1;
UPDATE PackagePublishingHistory SET pocket=10 WHERE pocket=2;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,08,0);

