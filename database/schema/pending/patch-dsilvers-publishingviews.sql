/*
 * Lucille's publishing system needs a few useful views so that it can get on
 * with publishing without performing many skanky SQLObject requests which
 * would slow things down
 */

DROP VIEW PendingSourcePackageFile;

CREATE VIEW PendingSourcePackageFile AS SELECT
LibraryFileAlias.id || '.' || SourcePackagePublishing.id  AS id,
           DistroRelease.distribution AS distribution,
           SourcePackagePublishing.id AS sourcepackagepublishing,
 SourcePackageReleaseFile.libraryfile AS libraryfilealias,
            LibraryFileAlias.filename AS libraryfilealiasfilename,
               SourcePackageName.name AS sourcepackagename,
                       Component.name AS componentname

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

DROP VIEW PendingBinaryPackageFile;

CREATE VIEW PendingBinaryPackageFile AS SELECT
LibraryFileAlias.id || '.' || PackagePublishing.id AS id,
DistroRelease.distribution AS distribution,
PackagePublishing.id AS packagepublishing,
Component.name as componentname,
LibraryFileAlias.filename as libraryfilealiasfilename,
SourcePackageName.name AS sourcepackagename,
BinaryPackageFile.libraryfile AS libraryfilealias

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

DROP VIEW PublishedSourcePackage;

CREATE VIEW PublishedSourcePackage AS SELECT
SourcePackagePublishing.id AS id,
        DistroRelease.name AS distroreleasename,
    SourcePackageName.name AS sourcepackagename,
            Component.name AS componentname,
              Section.name AS sectionname,
DistroRelease.distribution AS distribution

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

DROP VIEW PublishedBinaryPackage;

CREATE VIEW PublishedBinaryPackage AS SELECT
      PackagePublishing.id AS id,
        DistroRelease.name AS distroreleasename,
    BinaryPackageName.name AS binarypackagename,
            Component.name AS componentname,
              Section.name AS sectionname,
PackagePublishing.priority AS priority,
DistroRelease.distribution AS distribution

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

-- ------------------------------------------------------------------------- --
-- ------------------------------------------------------------------------- --
-- ------------------------------------------------------------------------- --

DROP VIEW PublishedSourcePackageFile;

CREATE VIEW PublishedSourcePackageFile AS SELECT
LibraryFileAlias.id || '.' || SourcePackagePublishing.id  AS id,
		   DistroRelease.name AS distroreleasename,
                       Component.name AS componentname,
               SourcePackageName.name AS sourcepackagename,
            LibraryFileAlias.filename AS libraryfilealiasfilename,
           DistroRelease.distribution AS distribution

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
-- In dbschema.py status of 2 or 3 are published to the overrides
  AND ( SourcePackagePublishing.status = 2
   OR   SourcePackagePublishing.status = 3
      )
  AND SourcePackageRelease.sourcepackage = SourcePackage.id
  AND SourcePackageName.id = SourcePackage.sourcepackagename
  AND Component.id = SourcePackagePublishing.component
;

-- ------------------------------------------------------------------------- --

DROP VIEW PublishedBinaryPackageFile;

CREATE VIEW PublishedBinaryPackageFile AS SELECT
LibraryFileAlias.id || '.' || PackagePublishing.id AS id,
               DistroRelease.name AS distroreleasename,
DistroArchRelease.architecturetag AS architecturetag,
                   Component.name AS componentname,
           SourcePackageName.name AS sourcepackagename,
        LibraryFileAlias.filename AS libraryfilealiasfilename,
       DistroRelease.distribution AS distribution

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
-- In dbschema.py status of 2 or 3 is published to the overrides
  AND ( PackagePublishing.status = 2
   OR   PackagePublishing.status = 3
      )

;

