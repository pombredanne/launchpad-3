/*
 * Lucille's publishing system needs a few useful views so that it can get on
 * with publishing without performing many skanky SQLObject requests which
 * would slow things down
 */

DROP VIEW SourcePackageFilesToPublish;

CREATE VIEW SourcePackageFilesToPublish AS SELECT
LibraryFileAlias.id || '.' || SourcePackagePublishing.id  AS id,
           DistroRelease.distribution AS drd,
           SourcePackagePublishing.id AS sppid,
 SourcePackageReleaseFile.libraryfile AS pfalias,
            LibraryFileAlias.filename AS lfaname,
               SourcePackageName.name AS spname,
                       Component.name AS cname

FROM SourcePackagePublishing,
     SourcePackageRelease,
     SourcePackageReleaseFile,
     LibraryFileAlias,
     DistroRelease,
     SourcePackage,
     SourcePackageName,
     Component

WHERE SourcePackagePublishing.distrorelease = DistroRelease.id
  AND SourcePackagePublishing.sourcepackagerelease = SourcePackageRelease.id
  AND SourcePackageReleaseFile.sourcepackagerelease = SourcePackageRelease.id
  AND LibraryFileAlias.id = SourcePackageReleaseFile.libraryfile
-- In dbschema.py status of 1 is defined as 'Pending Publishing'
  AND SourcePackagePublishing.status = 1
  AND SourcePackageRelease.sourcepackage = SourcePackage.id
  AND SourcePackageName.id = SourcePackage.sourcepackagename
  AND Component.id = SourcePackagePublishing.component
;

-- ------------------------------------------------------------------------- --

DROP VIEW BinaryPackageFilesToPublish;

CREATE VIEW BinaryPackageFilesToPublish AS SELECT
LibraryFileAlias.id || '.' || PackagePublishing.id AS id,
DistroRelease.distribution AS drd,
PackagePublishing.id AS ppid,
Component.name as cname,
LibraryFileAlias.filename as lfaname,
SourcePackageName.name AS spname,
BinaryPackageFile.libraryfile AS pfalias

FROM PackagePublishing,
     SourcePackage,
     SourcePackageRelease,
     SourcePackageName,
     Build,
     BinaryPackage,
     BinaryPackageFile,
     LibraryFileAlias,
     DistroArchRelease,
     DistroRelease,
     Component

WHERE DistroRelease.id = DistroArchRelease.distrorelease
  AND PackagePublishing.distroarchrelease = DistroArchRelease.id
  AND PackagePublishing.binarypackage = BinaryPackage.id
  AND BinaryPackageFile.binarypackage = BinaryPackage.id
  AND BinaryPackageFile.libraryfile = LibraryFileAlias.id
  AND BinaryPackage.build = Build.id
  AND Build.sourcepackagerelease = SourcePackageRelease.id
  AND SourcePackageRelease.sourcepackage = SourcePackage.id
  AND Component.id = PackagePublishing.component
  AND SourcePackageName.id = SourcePackage.sourcepackagename
-- In dbschema.py status of 1 is defined as 'Pending Publishing'
  AND PackagePublishing.status = 1

;

-- ------------------------------------------------------------------------- --
-- ------------------------------------------------------------------------- --
-- ------------------------------------------------------------------------- --

DROP VIEW PublishedSourcePackageOverrides;

CREATE VIEW PublishedSourcePackageOverrides AS SELECT
SourcePackagePublishing.id AS id,
DistroRelease.name AS drname,
SourcePackageName.name AS spname,
Component.name AS cname,
Section.name AS sname,
DistroRelease.distribution AS distro

FROM

SourcePackagePublishing,
DistroRelease,
SourcePackageRelease,
SourcePackage,
SourcePackageName,
Component,
Section

WHERE SourcePackagePublishing.distrorelease = DistroRelease.id
  AND SourcePackagePublishing.sourcepackagerelease = SourcePackageRelease.id
  AND SourcePackageRelease.sourcepackage = SourcePackage.id
  AND SourcePackage.sourcepackagename = SourcePackageName.id
  AND SourcePackagePublishing.component = Component.id
  AND SourcePackagePublishing.section = Section.id
  -- Status of 2 == Published, 3 == Superceded
  -- Any other status is not published into the overrides
  AND ( SourcePackagePublishing.status = 2
     OR SourcePackagePublishing.status = 3
      )
;

-- ------------------------------------------------------------------------- --

DROP VIEW PublishedBinaryPackageOverrides;

CREATE VIEW PublishedBinaryPackageOverrides AS SELECT
PackagePublishing.id AS id,
DistroRelease.name AS drname,
BinaryPackageName.name AS bpname,
Component.name AS cname,
Section.name AS sname,
PackagePublishing.priority AS priority,
DistroRelease.distribution AS distro

FROM
PackagePublishing,
DistroRelease,
DistroArchRelease,
BinaryPackage,
BinaryPackageName,
Component,
Section

WHERE PackagePublishing.distroarchrelease = DistroArchRelease.id
  AND DistroArchRelease.distrorelease = DistroRelease.id
  AND PackagePublishing.binarypackage = BinaryPackage.id
  AND BinaryPackage.binarypackagename = BinaryPackageName.id
  AND PackagePublishing.component = Component.id
  AND PackagePublishing.section = Section.id

  -- Status of 2 == Published, 3 == Superceded
  -- Any other status is not published into the overrides
  AND ( PackagePublishing.status = 2
     OR PackagePublishing.status = 3
      )
;
