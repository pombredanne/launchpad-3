/*
 * Lucille's publishing system needs a few useful views so that it can get on
 * with publishing without performing many skanky SQLObject requests which
 * would slow things down
 */

CREATE VIEW SourcePackageFilePublishing AS SELECT
LibraryFileAlias.id || '.' || SourcePackagePublishing.id  AS id,
           DistroRelease.distribution AS distribution,
           SourcePackagePublishing.id AS sourcepackagepublishing,
 SourcePackageReleaseFile.libraryfile AS libraryfilealias,
            LibraryFileAlias.filename AS libraryfilealiasfilename,
               SourcePackageName.name AS sourcepackagename,
                       Component.name AS componentname,
		   DistroRelease.name AS distroreleasename,
       SourcePackagePublishing.status AS publishingstatus

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
  AND SourcePackageRelease.sourcepackage = SourcePackage.id
  AND SourcePackageName.id = SourcePackage.sourcepackagename
  AND Component.id = SourcePackagePublishing.component
;

-- ------------------------------------------------------------------------- --

CREATE VIEW BinaryPackageFilePublishing AS SELECT
LibraryFileAlias.id || '.' || PackagePublishing.id AS id,
                        DistroRelease.distribution AS distribution,
                              PackagePublishing.id AS packagepublishing,
                                    Component.name AS componentname,
                         LibraryFileAlias.filename AS libraryfilealiasfilename,
                            SourcePackageName.name AS sourcepackagename,
                     BinaryPackageFile.libraryfile AS libraryfilealias,
                                DistroRelease.name AS distroreleasename,
                 DistroArchRelease.architecturetag AS architecturetag,
                          PackagePublishing.status AS publishingstatus
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

;

-- ------------------------------------------------------------------------- --
-- ------------------------------------------------------------------------- --
-- ------------------------------------------------------------------------- --

CREATE VIEW SourcePackagePublishingView AS SELECT
    SourcePackagePublishing.id AS id,
            DistroRelease.name AS distroreleasename,
        SourcePackageName.name AS sourcepackagename,
                Component.name AS componentname,
                  Section.name AS sectionname,
    DistroRelease.distribution AS distribution,
SourcePackagePublishing.status AS publishingstatus

FROM SourcePackagePublishing,
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
;

-- ------------------------------------------------------------------------- --

CREATE VIEW BinaryPackagePublishingView AS SELECT
      PackagePublishing.id AS id,
        DistroRelease.name AS distroreleasename,
    BinaryPackageName.name AS binarypackagename,
            Component.name AS componentname,
              Section.name AS sectionname,
PackagePublishing.priority AS priority,
DistroRelease.distribution AS distribution,
  PackagePublishing.status AS publishingstatus

FROM PackagePublishing,
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
;

UPDATE launchpaddatabaserevision SET major=4, minor=12, patch=0;

