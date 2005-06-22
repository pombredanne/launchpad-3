SET client_min_messages=ERROR;

/*
 * Fix up the SPPH counter because otherwise it'll explode later
 */

SELECT setval('sourcepackagepublishinghistory_id_seq',
    (select max(id)+1 from sourcepackagepublishinghistory));
DROP SEQUENCE sourcepackagepublishing_id_seq;

/*
 * Change the PackagePublishing table into a view onto the
 * PackagePublishingHistory table
 */
 

-- We assume that the PPH table's status column is not 7 (Removed) when
-- we want records in PP

-- Drop the things which rely on PackagePublishing...

DROP VIEW binarypackagefilepublishing;
DROP VIEW publishedpackageview;
DROP VIEW binarypackagepublishingview;

-- Migrate content from PP to PPH

-- 1. Create PPH

CREATE TABLE PackagePublishingHistory (
    id                    serial PRIMARY KEY,
    binarypackage         integer NOT NULL
            CONSTRAINT packagepublishinghistory_binarypackage_fk
            REFERENCES BinaryPackage,
    distroarchrelease     integer NOT NULL
            CONSTRAINT packagepublishinghistory_distroarchrelease_fk
            REFERENCES DistroArchRelease,
    status                integer NOT NULL, -- dbschema.PackagePublishingStatus
    component             integer NOT NULL
            CONSTRAINT sourcepackagepublishinghistory_component_fk
            REFERENCES Component,
    section               integer NOT NULL
            CONSTRAINT sourcepackagepublishinghistory_section_fk
            REFERENCES Section,
    priority              integer NOT NULL, -- dbschema.BinaryPackagePriority
    datecreated           timestamp without time zone NOT NULL,
    datepublished         timestamp without time zone,
    datesuperseded        timestamp without time zone,
    supersededby          integer
            CONSTRAINT packagepublishinghistory_supersededby_fk
            REFERENCES Build,
    datemadepending       timestamp without time zone,
    scheduleddeletiondate timestamp without time zone,
    dateremoved           timestamp without time zone
);

-- 2. Copy the data as-is
INSERT INTO PackagePublishingHistory 
 (id, distroarchrelease, binarypackage, status, component, section, priority,
  datepublished, scheduleddeletiondate, datecreated)
SELECT id, distroarchrelease, binarypackage, status, component, section, 
       priority, datepublished, scheduleddeletiondate, 
       coalesce(datepublished,'now'::timestamp without time zone)
  FROM PackagePublishing;

-- 2. For anything which is PUBLISHED, ensure it has a datepublished
UPDATE PackagePublishingHistory SET datepublished = 'now'::timestamp without time zone WHERE datepublished IS NULL AND status > 1;
-- 3. For anything which is SUPERSEDED, fill out the datesuperseded at least
UPDATE PackagePublishingHistory SET datesuperseded = 'now'::timestamp without time zone WHERE datesuperseded IS NULL AND status > 2;
-- 4. For anything where it is PENDINGREMOVAL, fill out datemadepending
UPDATE PackagePublishingHistory SET datemadepending = scheduleddeletiondate - '1 day'::interval WHERE datemadepending IS NULL AND status > 3;

-- 5. Fix up the sequence counter...

SELECT setval('packagepublishinghistory_id_seq',
    (select max(id)+1 from packagepublishinghistory));

-- And PP itself

DROP TABLE PackagePublishing;

-- Now re-create PP as a view onto PPH

CREATE OR REPLACE VIEW PackagePublishing AS SELECT
  id, distroarchrelease, binarypackage, status, component, section, priority,
  datepublished, scheduleddeletiondate FROM PackagePublishingHistory
  WHERE status != 7;

-- Now recreate the above views on PP (these are stolen from the dumped sql)

CREATE VIEW binarypackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (packagepublishing.id)::text) AS id, distrorelease.distribution, packagepublishing.id AS packagepublishing, component.name AS componentname, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, binarypackagefile.libraryfile AS libraryfilealias, distrorelease.name AS distroreleasename, distroarchrelease.architecturetag, packagepublishing.status AS publishingstatus FROM (((((((((packagepublishing JOIN binarypackage ON ((packagepublishing.binarypackage = binarypackage.id))) JOIN build ON ((binarypackage.build = build.id))) JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN binarypackagefile ON ((binarypackagefile.binarypackage = binarypackage.id))) JOIN libraryfilealias ON ((binarypackagefile.libraryfile = libraryfilealias.id))) JOIN distroarchrelease ON ((packagepublishing.distroarchrelease = distroarchrelease.id))) JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id))) JOIN component ON ((packagepublishing.component = component.id)));

CREATE VIEW publishedpackageview AS
    SELECT packagepublishing.id, distrorelease.distribution, distrorelease.id AS distrorelease, distrorelease.name AS distroreleasename, processorfamily.id AS processorfamily, processorfamily.name AS processorfamilyname, packagepublishing.status AS packagepublishingstatus, component.name AS component, section.name AS section, binarypackage.id AS binarypackage, binarypackagename.name AS binarypackagename, binarypackage.summary AS binarypackagesummary, binarypackage.description AS binarypackagedescription, binarypackage."version" AS binarypackageversion, build.id AS build, build.datebuilt, sourcepackagerelease.id AS sourcepackagerelease, sourcepackagerelease."version" AS sourcepackagereleaseversion, sourcepackagename.name AS sourcepackagename, binarypackage.fti AS binarypackagefti FROM ((((((((((packagepublishing JOIN distroarchrelease ON ((distroarchrelease.id = packagepublishing.distroarchrelease))) JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id))) JOIN processorfamily ON ((distroarchrelease.processorfamily = processorfamily.id))) JOIN component ON ((packagepublishing.component = component.id))) JOIN binarypackage ON ((packagepublishing.binarypackage = binarypackage.id))) JOIN section ON ((packagepublishing.section = section.id))) JOIN binarypackagename ON ((binarypackage.binarypackagename = binarypackagename.id))) JOIN build ON ((binarypackage.build = build.id))) JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)));

CREATE VIEW binarypackagepublishingview AS
    SELECT packagepublishing.id, distrorelease.name AS distroreleasename, binarypackagename.name AS binarypackagename, component.name AS componentname, section.name AS sectionname, packagepublishing.priority, distrorelease.distribution, packagepublishing.status AS publishingstatus FROM packagepublishing, distrorelease, distroarchrelease, binarypackage, binarypackagename, component, section WHERE ((((((packagepublishing.distroarchrelease = distroarchrelease.id) AND (distroarchrelease.distrorelease = distrorelease.id)) AND (packagepublishing.binarypackage = binarypackage.id)) AND (binarypackage.binarypackagename = binarypackagename.id)) AND (packagepublishing.component = component.id)) AND (packagepublishing.section = section.id));


-- Now create the indexes on pph needed to support what *was* on pp

CREATE INDEX packagepublishinghistory_binarypackage_key ON packagepublishinghistory(binarypackage);

CREATE INDEX packagepublishinghistory_component_key ON packagepublishinghistory(component);

CREATE INDEX packagepublishinghistory_distroarchrelease_key ON packagepublishinghistory(distroarchrelease);

CREATE INDEX packagepublishinghistory_section_key ON packagepublishinghistory(section);

CREATE INDEX packagepublishinghistory_status_key ON packagepublishinghistory(status);

-- Finally, update the db revision

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 05, 0);
