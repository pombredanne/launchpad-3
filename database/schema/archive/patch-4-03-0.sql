/* VSourcePackageReleasePublishing is broken. This patch will drop and
 * then recreate it fixed.
 */

DROP VIEW VSourcePackageReleasePublishing;

CREATE VIEW VSourcePackageReleasePublishing AS
SELECT 
    sourcepackagerelease.id, 
    sourcepackagename.name,
    sourcepackage.shortdesc, 
    sourcepackage.maintainer,
    sourcepackage.description, 
    sourcepackage.id AS sourcepackage,
    sourcepackagepublishing.status AS publishingstatus,
    sourcepackagepublishing.datepublished,
    sourcepackagerelease.architecturehintlist,
    sourcepackagerelease."version", 
    sourcepackagerelease.creator,
    sourcepackagerelease.section, 
    sourcepackagerelease.component,
    sourcepackagerelease.changelog, 
    sourcepackagerelease.builddepends,
    sourcepackagerelease.builddependsindep, 
    sourcepackagerelease.urgency,
    sourcepackagerelease.dateuploaded, 
    sourcepackagerelease.dsc,
    sourcepackagerelease.dscsigningkey,
    distrorelease.id AS distrorelease, 
    component.name AS componentname
FROM sourcepackagepublishing, 
    sourcepackagerelease, 
    component,
    sourcepackage, 
    distrorelease,
    sourcepackagename
WHERE 
        sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id 
    AND sourcepackagerelease.sourcepackage = sourcepackage.id 
    AND sourcepackagepublishing.distrorelease = distrorelease.id 
    AND sourcepackage.sourcepackagename = sourcepackagename.id 
    AND component.id = sourcepackagerelease.component;

