SET client_min_messages=ERROR;

/* Just like SourcePackagePublishing */
BEGIN;
DROP VIEW vsourcepackagereleasepublishing ;
CREATE VIEW vsourcepackagereleasepublishing as SELECT sourcepackagerelease.id, sourcepackagename.name, sourcepackage.shortdesc, sourcepackage.maintainer, sourcepackage.description, sourcepackage.id AS sourcepackage, sourcepackagepublishing.status AS publishingstatus, sourcepackagepublishing.datepublished, sourcepackagerelease.architecturehintlist, sourcepackagerelease."version", sourcepackagerelease.creator, sourcepackagerelease.section, sourcepackagerelease.component, sourcepackagerelease.changelog, sourcepackagerelease.builddepends, sourcepackagerelease.builddependsindep, sourcepackagerelease.manifest, sourcepackagerelease.urgency, sourcepackagerelease.dateuploaded, sourcepackagerelease.dsc, sourcepackagerelease.dscsigningkey, distrorelease.id AS distrorelease, component.name AS componentname
FROM sourcepackagepublishing, sourcepackagerelease, component, sourcepackage, distrorelease, sourcepackagename
WHERE sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id AND sourcepackagerelease.sourcepackage = sourcepackage.id AND sourcepackagepublishing.distrorelease = distrorelease.id AND sourcepackage.sourcepackagename = sourcepackagename.id AND component.id = sourcepackagerelease.component;
COMMENT ON VIEW VSourcePackageReleasePublishing IS 'This view simplifies a lot of queries relating to publishing and is for use as a replacement for SourcePackageRelease (I actually intend to move it to a subclass of SourcePackageRelease, because using a View in place of a real table is bizarre).';
END;
