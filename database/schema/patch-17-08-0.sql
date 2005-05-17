/*
 * Pockets and Embargo support
 *
 * Needed for DistroReleaseUpdates and SecurityReleasesWithoutGettingShot
 */

SET client_min_messages=ERROR;
	
-- First up, add the Pocket column to SPPH and PPH
-- Note that pocket zero is the 'PLAIN' pocket which implies no suffix

ALTER TABLE SourcePackagePublishingHistory ADD COLUMN pocket INTEGER;
UPDATE      SourcePackagePublishingHistory SET pocket=0 WHERE pocket IS NULL;
ALTER TABLE SourcePackagePublishingHistory ALTER COLUMN pocket SET NOT NULL;
ALTER TABLE SourcePackagePublishingHistory ALTER COLUMN pocket SET DEFAULT 0;

ALTER TABLE PackagePublishingHistory ADD COLUMN pocket INTEGER;
UPDATE      PackagePublishingHistory SET pocket=0 WHERE pocket IS NULL;
ALTER TABLE PackagePublishingHistory ALTER COLUMN pocket SET NOT NULL;
ALTER TABLE PackagePublishingHistory ALTER COLUMN pocket SET DEFAULT 0;

-- Now we need an embargo column...

ALTER TABLE SourcePackagePublishingHistory ADD COLUMN embargo BOOLEAN;
UPDATE      SourcePackagePublishingHistory SET embargo=FALSE 
	    WHERE embargo IS NULL;
ALTER TABLE SourcePackagePublishingHistory ALTER COLUMN embargo SET NOT NULL;
ALTER TABLE SourcePackagePublishingHistory ALTER COLUMN 
	    embargo SET DEFAULT FALSE;

ALTER TABLE PackagePublishingHistory ADD COLUMN embargo BOOLEAN;
UPDATE      PackagePublishingHistory SET embargo=FALSE WHERE embargo IS NULL;
ALTER TABLE PackagePublishingHistory ALTER COLUMN embargo SET NOT NULL;
ALTER TABLE PackagePublishingHistory ALTER COLUMN embargo SET DEFAULT FALSE;

-- Because vendorsec are very careful about when embargo lifting takes place
-- we need to record when we lifted an embargo so that we can be sure we're not
-- being naughty...

-- embargolifted can be NULL if we've never lifted an embargo.
ALTER TABLE SourcePackagePublishingHistory ADD COLUMN 
            embargolifted TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE PackagePublishingHistory ADD COLUMN 
            embargolifted TIMESTAMP WITHOUT TIME ZONE;

-- Fix up the views for SPP and PP to include the pocket and exclude embargoed
-- publishing records...

-- 1. Drop all the views...
--    PackagePublishing...
DROP VIEW binarypackagefilepublishing;
DROP VIEW publishedpackageview;
DROP VIEW binarypackagepublishingview;
DROP VIEW PackagePublishing;

--    SourcePackagePublishing
DROP VIEW SourcePackageFilePublishing;
DROP VIEW SourcePackagePublishingView;
DROP VIEW VSourcePackageReleasePublishing;
DROP VIEW VSourcePackageInDistro;
DROP VIEW SourcePackagePublishing;

-- 2. Recreate the base views

CREATE OR REPLACE VIEW SourcePackagePublishing AS SELECT
  id, distrorelease, sourcepackagerelease, status, component, section,
  datepublished, scheduleddeletiondate, pocket 
  FROM SourcePackagePublishingHistory
  WHERE status != 7 AND embargo = FALSE;

CREATE OR REPLACE VIEW PackagePublishing AS SELECT
  id, distroarchrelease, binarypackage, status, component, section, priority,
  datepublished, scheduleddeletiondate, pocket
  FROM PackagePublishingHistory
  WHERE status != 7 AND embargo = FALSE;

-- 3. PackagePublishing views...

CREATE VIEW binarypackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (packagepublishing.id)::text) AS id, distrorelease.distribution, packagepublishing.id AS packagepublishing, component.name AS componentname, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, binarypackagefile.libraryfile AS libraryfilealias, distrorelease.name AS distroreleasename, distroarchrelease.architecturetag, packagepublishing.status AS publishingstatus FROM (((((((((packagepublishing JOIN binarypackage ON ((packagepublishing.binarypackage = binarypackage.id))) JOIN build ON ((binarypackage.build = build.id))) JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN binarypackagefile ON ((binarypackagefile.binarypackage = binarypackage.id))) JOIN libraryfilealias ON ((binarypackagefile.libraryfile = libraryfilealias.id))) JOIN distroarchrelease ON ((packagepublishing.distroarchrelease = distroarchrelease.id))) JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id))) JOIN component ON ((packagepublishing.component = component.id)));

CREATE VIEW publishedpackageview AS
    SELECT packagepublishing.id, distrorelease.distribution, distrorelease.id AS distrorelease, distrorelease.name AS distroreleasename, processorfamily.id AS processorfamily, processorfamily.name AS processorfamilyname, packagepublishing.status AS packagepublishingstatus, component.name AS component, section.name AS section, binarypackage.id AS binarypackage, binarypackagename.name AS binarypackagename, binarypackage.summary AS binarypackagesummary, binarypackage.description AS binarypackagedescription, binarypackage."version" AS binarypackageversion, build.id AS build, build.datebuilt, sourcepackagerelease.id AS sourcepackagerelease, sourcepackagerelease."version" AS sourcepackagereleaseversion, sourcepackagename.name AS sourcepackagename, binarypackage.fti AS binarypackagefti FROM ((((((((((packagepublishing JOIN distroarchrelease ON ((distroarchrelease.id = packagepublishing.distroarchrelease))) JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id))) JOIN processorfamily ON ((distroarchrelease.processorfamily = processorfamily.id))) JOIN component ON ((packagepublishing.component = component.id))) JOIN binarypackage ON ((packagepublishing.binarypackage = binarypackage.id))) JOIN section ON ((packagepublishing.section = section.id))) JOIN binarypackagename ON ((binarypackage.binarypackagename = binarypackagename.id))) JOIN build ON ((binarypackage.build = build.id))) JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)));

CREATE VIEW binarypackagepublishingview AS
    SELECT packagepublishing.id, distrorelease.name AS distroreleasename, binarypackagename.name AS binarypackagename, component.name AS componentname, section.name AS sectionname, packagepublishing.priority, distrorelease.distribution, packagepublishing.status AS publishingstatus FROM packagepublishing, distrorelease, distroarchrelease, binarypackage, binarypackagename, component, section WHERE ((((((packagepublishing.distroarchrelease = distroarchrelease.id) AND (distroarchrelease.distrorelease = distrorelease.id)) AND (packagepublishing.binarypackage = binarypackage.id)) AND (binarypackage.binarypackagename = binarypackagename.id)) AND (packagepublishing.component = component.id)) AND (packagepublishing.section = section.id));

-- 4. SourcePackagePublishing views

CREATE VIEW sourcepackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (sourcepackagepublishing.id)::text) AS id, distrorelease.distribution, sourcepackagepublishing.id AS sourcepackagepublishing, sourcepackagereleasefile.libraryfile AS libraryfilealias, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, component.name AS componentname, distrorelease.name AS distroreleasename, sourcepackagepublishing.status AS publishingstatus FROM ((((((sourcepackagepublishing JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN sourcepackagereleasefile ON ((sourcepackagereleasefile.sourcepackagerelease = sourcepackagerelease.id))) JOIN libraryfilealias ON ((libraryfilealias.id = sourcepackagereleasefile.libraryfile))) JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN component ON ((sourcepackagepublishing.component = component.id)));

CREATE VIEW sourcepackagepublishingview AS
    SELECT sourcepackagepublishing.id, distrorelease.name AS distroreleasename, sourcepackagename.name AS sourcepackagename, component.name AS componentname, section.name AS sectionname, distrorelease.distribution, sourcepackagepublishing.status AS publishingstatus FROM (((((sourcepackagepublishing JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN component ON ((sourcepackagepublishing.component = component.id))) JOIN section ON ((sourcepackagepublishing.section = section.id)));

CREATE VIEW vsourcepackagereleasepublishing AS
    SELECT DISTINCT sourcepackagerelease.id, sourcepackagename.name, maintainership.maintainer, sourcepackagepublishing.status AS publishingstatus, sourcepackagepublishing.datepublished, sourcepackagepublishing.distrorelease, component.name AS componentname, sourcepackagerelease.architecturehintlist, sourcepackagerelease."version", sourcepackagerelease.creator, sourcepackagerelease.format, sourcepackagerelease.manifest, sourcepackagerelease.section, sourcepackagerelease.component, sourcepackagerelease.changelog, sourcepackagerelease.builddepends, sourcepackagerelease.builddependsindep, sourcepackagerelease.urgency, sourcepackagerelease.dateuploaded, sourcepackagerelease.dsc, sourcepackagerelease.dscsigningkey, sourcepackagerelease.uploaddistrorelease, sourcepackagerelease.sourcepackagename FROM (((((sourcepackagepublishing JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN component ON ((sourcepackagepublishing.component = component.id))) LEFT JOIN maintainership ON (((sourcepackagerelease.sourcepackagename = maintainership.sourcepackagename) AND (distrorelease.distribution = maintainership.distribution)))) ORDER BY sourcepackagerelease.id, sourcepackagename.name, maintainership.maintainer, sourcepackagepublishing.status, sourcepackagepublishing.datepublished, sourcepackagepublishing.distrorelease, component.name, sourcepackagerelease.architecturehintlist, sourcepackagerelease."version", sourcepackagerelease.creator, sourcepackagerelease.format, sourcepackagerelease.manifest, sourcepackagerelease.section, sourcepackagerelease.component, sourcepackagerelease.changelog, sourcepackagerelease.builddepends, sourcepackagerelease.builddependsindep, sourcepackagerelease.urgency, sourcepackagerelease.dateuploaded, sourcepackagerelease.dsc, sourcepackagerelease.dscsigningkey, sourcepackagerelease.uploaddistrorelease, sourcepackagerelease.sourcepackagename;

CREATE VIEW vsourcepackageindistro AS
    SELECT sourcepackagerelease.id, sourcepackagerelease.manifest, sourcepackagerelease.format, sourcepackagerelease.sourcepackagename, sourcepackagename.name, sourcepackagepublishing.distrorelease, distrorelease.distribution FROM (((sourcepackagepublishing JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)));

-- Finally, let's have some indexes...

CREATE INDEX packagepublishinghistory_pocket_idx
          ON packagepublishinghistory(pocket);

CREATE INDEX sourcepackagepublishinghistory_pocket_idx
          ON sourcepackagepublishinghistory(pocket);

-- Finally, update the db revision

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 8, 0);
