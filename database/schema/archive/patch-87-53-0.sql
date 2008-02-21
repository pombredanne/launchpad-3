SET client_min_messages=ERROR;

ALTER TABLE SourcePackageRelease
  DROP COLUMN manifest;
ALTER TABLE ProductRelease
  DROP COLUMN manifest;


-- Not used any more (if ever).
DROP TABLE DevelopmentManifest;
DROP TABLE ManifestAncestry;
DROP TABLE ManifestEntry;
DROP TABLE Manifest;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 53, 0);
