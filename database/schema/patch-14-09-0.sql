/*
 * Change the SourcePackagePublishing table into a view onto the
 * SourcePackagePublishingHistory table
 */
 
SET client_min_messages=ERROR;

-- We assume that the SPPH table's status column is not 7 (Removed) when
-- we want records in SPP

-- Drop the things which rely on SourcePackagePublishing...

DROP VIEW SourcePackageFilePublishing;
DROP VIEW SourcePackagePublishingView;
DROP VIEW VSourcePackageReleasePublishing;
DROP VIEW VSourcePackageInDistro;

-- Migrate content from SPP to SPPH

-- 1. Copy the data as-is
INSERT INTO SourcePackagePublishingHistory 
 (id, distrorelease, sourcepackagerelease, status, component, section,
  datepublished, scheduleddeletiondate, datecreated)
SELECT id, distrorelease, sourcepackagerelease, status, component, section,
       datepublished, scheduleddeletiondate, coalesce(datepublished,'now'::timestamp without time zone)
  FROM SourcePackagePublishing;

-- 2. For anything which is PUBLISHED, ensure it has a datepublished
UPDATE SourcePackagePublishingHistory SET datepublished = 'now'::timestamp without time zone WHERE datepublished IS NULL AND status > 1;
-- 3. For anything which is SUPERSEDED, fill out the datesuperseded at least
UPDATE SourcePackagePublishingHistory SET datesuperseded = 'now'::timestamp without time zone WHERE datesuperseded IS NULL AND status > 2;
-- 4. For anything where it is PENDINGREMOVAL, fill out datemadepending
UPDATE SourcePackagePublishingHistory SET datemadepending = scheduleddeletiondate - '1 day'::interval WHERE datemadepending IS NULL AND status > 3;

-- And SPP itself

DROP TABLE SourcePackagePublishing;

-- Now re-create SPP as a view onto SPPH

CREATE OR REPLACE VIEW SourcePackagePublishing AS SELECT
  id, distrorelease, sourcepackagerelease, status, component, section,
  datepublished, scheduleddeletiondate FROM SourcePackagePublishingHistory
  WHERE status != 7;

-- Now recreate the above views on SPP (these are stolen from the dumped sql)

CREATE VIEW sourcepackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (sourcepackagepublishing.id)::text) AS id, distrorelease.distribution, sourcepackagepublishing.id AS sourcepackagepublishing, sourcepackagereleasefile.libraryfile AS libraryfilealias, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, component.name AS componentname, distrorelease.name AS distroreleasename, sourcepackagepublishing.status AS publishingstatus FROM ((((((sourcepackagepublishing JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN sourcepackagereleasefile ON ((sourcepackagereleasefile.sourcepackagerelease = sourcepackagerelease.id))) JOIN libraryfilealias ON ((libraryfilealias.id = sourcepackagereleasefile.libraryfile))) JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN component ON ((sourcepackagepublishing.component = component.id)));

CREATE VIEW sourcepackagepublishingview AS
    SELECT sourcepackagepublishing.id, distrorelease.name AS distroreleasename, sourcepackagename.name AS sourcepackagename, component.name AS componentname, section.name AS sectionname, distrorelease.distribution, sourcepackagepublishing.status AS publishingstatus FROM (((((sourcepackagepublishing JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN component ON ((sourcepackagepublishing.component = component.id))) JOIN section ON ((sourcepackagepublishing.section = section.id)));
CREATE VIEW vsourcepackagereleasepublishing AS
    SELECT DISTINCT sourcepackagerelease.id, sourcepackagename.name, maintainership.maintainer, sourcepackagepublishing.status AS publishingstatus, sourcepackagepublishing.datepublished, sourcepackagepublishing.distrorelease, component.name AS componentname, sourcepackagerelease.architecturehintlist, sourcepackagerelease."version", sourcepackagerelease.creator, sourcepackagerelease.format, sourcepackagerelease.manifest, sourcepackagerelease.section, sourcepackagerelease.component, sourcepackagerelease.changelog, sourcepackagerelease.builddepends, sourcepackagerelease.builddependsindep, sourcepackagerelease.urgency, sourcepackagerelease.dateuploaded, sourcepackagerelease.dsc, sourcepackagerelease.dscsigningkey, sourcepackagerelease.uploaddistrorelease, sourcepackagerelease.sourcepackagename FROM (((((sourcepackagepublishing JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN component ON ((sourcepackagepublishing.component = component.id))) LEFT JOIN maintainership ON (((sourcepackagerelease.sourcepackagename = maintainership.sourcepackagename) AND (distrorelease.distribution = maintainership.distribution)))) ORDER BY sourcepackagerelease.id, sourcepackagename.name, maintainership.maintainer, sourcepackagepublishing.status, sourcepackagepublishing.datepublished, sourcepackagepublishing.distrorelease, component.name, sourcepackagerelease.architecturehintlist, sourcepackagerelease."version", sourcepackagerelease.creator, sourcepackagerelease.format, sourcepackagerelease.manifest, sourcepackagerelease.section, sourcepackagerelease.component, sourcepackagerelease.changelog, sourcepackagerelease.builddepends, sourcepackagerelease.builddependsindep, sourcepackagerelease.urgency, sourcepackagerelease.dateuploaded, sourcepackagerelease.dsc, sourcepackagerelease.dscsigningkey, sourcepackagerelease.uploaddistrorelease, sourcepackagerelease.sourcepackagename;

CREATE VIEW vsourcepackageindistro AS
    SELECT sourcepackagerelease.id, sourcepackagerelease.manifest, sourcepackagerelease.format, sourcepackagerelease.sourcepackagename, sourcepackagename.name, sourcepackagepublishing.distrorelease, distrorelease.distribution FROM (((sourcepackagepublishing JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)));

-- Now create the indexes on spph needed to support spp

CREATE INDEX sourcepackagepublishinghistory_distrorelease_key ON sourcepackagepublishinghistory(distrorelease);

CREATE INDEX sourcepackagepublishinghistory_status_key ON sourcepackagepublishinghistory(status);

CREATE INDEX sourcepackagepublishinghistory_sourcepackagerelease_key ON sourcepackagepublishinghistory(sourcepackagerelease);

INSERT INTO LaunchpadDatabaseRevision VALUES (14, 9, 0);
