SET client_min_messages=ERROR;

/* Just like SourcePackagePublishing */
DROP VIEW vsourcepackagereleasepublishing ;
CREATE VIEW vsourcepackagereleasepublishing AS 
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
        sourcepackagerelease.manifest,
        sourcepackagerelease.urgency,
        sourcepackagerelease.dateuploaded,
        sourcepackagerelease.dsc,
        sourcepackagerelease.dscsigningkey,
        distrorelease.id AS distrorelease,
        component.name AS componentname
    FROM
        sourcepackagepublishing, sourcepackagerelease, component,
        sourcepackage, distrorelease, sourcepackagename
    WHERE
        sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id
        AND sourcepackagerelease.sourcepackage = sourcepackage.id
        AND sourcepackagepublishing.distrorelease = distrorelease.id
        AND sourcepackage.sourcepackagename = sourcepackagename.id
        AND component.id = sourcepackagerelease.component;

/* Drop a temporary table that snuck out */

DROP TABLE archarchivelocation_bak;

INSERT INTO LaunchpadDatabaseRevision VALUES (10,5,0);

