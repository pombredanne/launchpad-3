SET client_min_messages=ERROR;

DROP INDEX sourcepackage_sourcepackagename_key;

/* Add a manifest column to sourcepackagerelease */
ALTER TABLE SourcePackageRelease ADD COLUMN manifest integer;
ALTER TABLE SourcePackageRelease 
    ADD CONSTRAINT sourcepackagerelease_manifest_fk
    FOREIGN KEY (manifest) REfERENCES Manifest(id);
UPDATE SourcepackageRelease SET manifest = (
    SELECT manifest FROM SourcePackage WHERE SourcePackage.id = sourcepackage);

/* Add a maintainer column to sourcepackagerelease */
ALTER TABLE SourcePackageRelease ADD COLUMN maintainer integer;
ALTER TABLE SourcePackageRelease ADD CONSTRAINT
    sourcepackagerelease_maintainer_fk
    FOREIGN KEY (maintainer) REFERENCES Person(id);
UPDATE SourcePackageRelease SET maintainer = (
    SELECT maintainer FROM SourcePackage
    WHERE SourcePackage.id = sourcepackage);
ALTER TABLE SourcePackageRelease ALTER COLUMN maintainer SET NOT NULL;

/* Add a name column to sourcepackagerelease */
ALTER TABLE SourcepackageRelease ADD COLUMN sourcepackagename integer;
ALTER TABLE SourcepackageRelease ADD CONSTRAINT
    sourcepackagerelease_sourcepackagename_fk
    FOREIGN KEY (sourcepackagename) REFERENCES SourcePackageName(id);
UPDATE SourcePackageRelease SET sourcepackagename=(
    SELECT sourcepackagename FROM SourcePackage
    WHERE SourcePackage.id = sourcepackage);
ALTER TABLE SourcepackageRelease ALTER COLUMN sourcepackagename SET NOT NULL;

ALTER TABLE SourcePackage ADD CONSTRAINT sourcepackage_distro_key
    UNIQUE (distro, sourcepackagename);

UPDATE LaunchpadDatabaseRevision SET major=6, minor=12, patch=0;

