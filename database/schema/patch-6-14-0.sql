
/* Views for kiko. Notes in comments.sql */

/* Ready to go except for what to call them? */

DROP VIEW VSourcePackageInDistro;

CREATE VIEW VSourcePackageInDistro AS
SELECT DISTINCT 
    sourcepackage.id, 
    sourcepackage.shortdesc,
    sourcepackage.description, 
    sourcepackage.distro,
    sourcepackage.manifest, 
    sourcepackage.maintainer,
    sourcepackage.srcpackageformat,
    sourcepackagename.id AS sourcepackagename, 
    sourcepackagename.name,
    distrorelease.id AS distrorelease
FROM 
    sourcepackagepublishing, 
    sourcepackagerelease, 
    sourcepackage,
    distrorelease, 
    sourcepackagename
WHERE 
    sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id 
AND sourcepackagerelease.sourcepackage = sourcepackage.id 
AND sourcepackagepublishing.distrorelease = distrorelease.id 
AND sourcepackage.sourcepackagename = sourcepackagename.id;

UPDATE LaunchpadDatabaseRevision SET major=6,minor=14,patch=0;