SET client_min_messages=ERROR;

ALTER TABLE ProductRelease ADD COLUMN manifest integer;
ALTER TABLE ProductRelease ADD CONSTRAINT productrelease_manifest_fk
    FOREIGN KEY (manifest) REFERENCES Manifest(id);

DROP TABLE CodeReleaseRelationship;
DROP TABLE CodeRelease;

UPDATE LaunchpadDatabaseRevision SET major=6,minor=13,patch=0;

