DROP VIEW publishedpackageview;

CREATE VIEW publishedpackageview AS
SELECT 	packagepublishing.id, 
	distroarchrelease.id AS distroarchrelease,
	distrorelease.distribution, 
	distrorelease.id AS distrorelease, 
	distrorelease.name AS distroreleasename, 
	processorfamily.id AS processorfamily, 
	processorfamily.name AS processorfamilyname, 
	packagepublishing.status AS packagepublishingstatus, 
	component.name AS component, 
	section.name AS section, 
	binarypackage.id AS binarypackage, 
	binarypackagename.name AS binarypackagename, 
	binarypackage.summary AS binarypackagesummary, 
	binarypackage.description AS binarypackagedescription, 
	binarypackage."version" AS binarypackageversion, 
	build.id AS build, 
	build.datebuilt, 
	sourcepackagerelease.id AS sourcepackagerelease, 
	sourcepackagerelease."version" AS sourcepackagereleaseversion, 
	sourcepackagename.name AS sourcepackagename, 
	binarypackage.fti AS binarypackagefti

   FROM packagepublishing

   JOIN distroarchrelease ON distroarchrelease.id = packagepublishing.distroarchrelease
   JOIN distrorelease ON distroarchrelease.distrorelease = distrorelease.id
   JOIN processorfamily ON distroarchrelease.processorfamily = processorfamily.id
   JOIN component ON packagepublishing.component = component.id
   JOIN binarypackage ON packagepublishing.binarypackage = binarypackage.id
   JOIN section ON packagepublishing.section = section.id
   JOIN binarypackagename ON binarypackage.binarypackagename = binarypackagename.id
   JOIN build ON binarypackage.build = build.id
   JOIN sourcepackagerelease ON build.sourcepackagerelease = sourcepackagerelease.id
   JOIN sourcepackagename ON sourcepackagerelease.sourcepackagename = sourcepackagename.id;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 04, 0);