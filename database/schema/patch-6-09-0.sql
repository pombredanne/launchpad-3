
/*
  This view gives us everything we need to query the set of packages that
  are currently published in a distrorelease.

  STUB: I thought it would be safe to move this view into permission as it
  is in any event read-only.
*/

SET client_min_messages TO error;

CREATE VIEW PublishedPackageView AS SELECT
       PackagePublishing.id AS id,
       DistroRelease.distribution AS distribution,
       DistroRelease.id AS distrorelease,
       DistroRelease.name AS distroreleasename,
       ProcessorFamily.id AS processorfamily,
       ProcessorFamily.name AS processorfamilyname,
       PackagePublishing.status AS packagepublishingstatus,
       Component.name AS component,
       Section.name AS section,
       BinaryPackage.id AS binarypackage,
       BinaryPackageName.name AS binarypackagename,
       BinaryPackage.shortdesc AS binarypackageshortdesc,
       BinaryPackage.description AS binarypackagedescription,
       BinaryPackage.version AS binarypackageversion,
       Build.id AS build,
       Build.datebuilt AS datebuilt,
       SourcePackageRelease.id AS sourcepackagerelease,
       SourcePackageRelease.version AS sourcepackagereleaseversion,
       SourcePackageRelease.sourcepackage AS sourcepackage,
       SourcePackageName.name AS sourcepackagename
   FROM
       DistroRelease, DistroArchRelease, ProcessorFamily,
       PackagePublishing, Component, Section, BinaryPackage,
       BinaryPackageName, Build, SourcePackageRelease,
       SourcePackage, SourcePackageName
   WHERE
       DistroArchRelease.distrorelease=DistroRelease.id AND
       DistroArchRelease.processorfamily=ProcessorFamily.id AND
       DistroArchRelease.id=PackagePublishing.distroarchrelease AND
       PackagePublishing.binarypackage=BinaryPackage.id AND
       PackagePublishing.component=Component.id AND
       PackagePublishing.section=Section.id AND
       BinaryPackage.build=Build.id AND
       BinaryPackage.binarypackagename=BinaryPackageName.id AND
       Build.sourcepackagerelease=SourcePackageRelease.id AND 
       SourcePackageRelease.sourcepackage=SourcePackage.id AND
       SourcePackage.sourcepackagename=SourcePackageName.id
       ;
   

UPDATE LaunchpadDatabaseRevision SET major=6,minor=9,patch=0;

