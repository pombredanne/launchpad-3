
/*
  This view gives us everything we need to query the set of packages that
  are currently published in a distrorelease.
*/

SET client_min_messages TO error;

/* Create full text index columns required for this patch to run. The
 * fti.py script will rebuild them *after* this patch is run, so we
 * don't actually have to get it perfect.
 */

ALTER TABLE BinaryPackage ADD COLUMN fti tsvector;
ALTER TABLE SourcePackage ADD COLUMN fti tsvector;

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
       SourcePackageName.name AS sourcepackagename,
       BinaryPackage.fti as binarypackagefti
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
       BinaryPackage.binarypackagename=BinaryPackageName.id AND
       BinaryPackage.build=Build.id AND
       Build.sourcepackagerelease=SourcePackageRelease.id AND 
       SourcePackageRelease.sourcepackage=SourcePackage.id AND
       SourcePackage.sourcepackagename=SourcePackageName.id
       ;

/* Create indexes to speed this up as much as possible. Need to see
   how this view performs with real data on doogfood.
 */
CREATE INDEX packagepublishing_component_idx
    ON PackagePublishing(component);
CREATE INDEX distroarchrelease_distrorelease_idx
    ON DistroArchRelease(distrorelease);
CREATE INDEX distroarchrelease_processorfamily_idx
    ON DistroArchRelease(processorfamily);
CREATE INDEX binarypackage_build_idx
    ON BinaryPackage(build);
CREATE INDEX sourcepackage_sourcepackagename_idx
    ON SourcePackage(sourcepackagename);
CREATE INDEX packagepublishing_section_idx
    ON PackagePublishing(section);
CREATE INDEX build_component_idx
    ON Build(sourcepackagerelease);
CREATE INDEX packagepublishing_distroarchrelease_idx
    ON PackagePublishing(distroarchrelease);

UPDATE LaunchpadDatabaseRevision SET major=6,minor=9,patch=0;

