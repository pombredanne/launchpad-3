
/* Views for kiko. Notes in comments.sql */

/* Ready to go except for what to call them? */

SELECT DISTINCT 
    sourcepackage.id, 
    sourcepackage.shortdesc,
    sourcepackage.description, 
    sourcepackage.distro,
    sourcepackage.manifest, 
    sourcepackage.maintainer,
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
    sourcepackagerelease.id AS sourcepackagerelease, 
    distrorelease.id AS distrorelease, 
    label.name AS componentname, 
    label.title AS componenttitle, 
    label.description AS componentdesc
FROM sourcepackagepublishing, 
    sourcepackagerelease, 
    label,
    sourcepackage, 
    distrorelease,
    sourcepackagename
WHERE 
        sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id 
    AND sourcepackagerelease.sourcepackage = sourcepackage.id 
    AND sourcepackagepublishing.distrorelease = distrorelease.id 
    AND sourcepackage.sourcepackagename = sourcepackagename.id 
    AND label.id = sourcepackagerelease.component;
