SET client_min_messages=ERROR;


-- Adding removal tracking support for source publications.
ALTER TABLE SecureSourcePackagePublishingHistory
    ADD COLUMN removed_by integer;
ALTER TABLE SecureSourcePackagePublishingHistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_removedby_fk
    FOREIGN KEY (removed_by) REFERENCES person(id);
ALTER TABLE SecureSourcePackagePublishingHistory
    ADD COLUMN removal_comment text;
CREATE INDEX securesourcepackagepublishinghistory__removed_by__idx
    ON SecureSourcePackagePublishingHistory(removed_by)
    WHERE removed_by IS NOT NULL;

-- Adding removal tracking support for binary publications.
ALTER TABLE SecureBinaryPackagePublishingHistory
    ADD COLUMN removed_by integer;
ALTER TABLE SecureBinaryPackagePublishingHistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_removedby_fk
    FOREIGN KEY (removed_by) REFERENCES person(id);
ALTER TABLE SecureBinaryPackagePublishingHistory
    ADD COLUMN removal_comment text;
CREATE INDEX securebinarypackagepublishinghistory__removed_by__idx 
    ON SecureBinaryPackagePublishingHistory(removed_by)
    WHERE removed_by IS NOT NULL;


-- Remove-for-editing
DROP VIEW SourcePackageFilePublishing;
DROP VIEW BinaryPackageFilePublishing;
DROP VIEW PublishedPackageView;

-- Removing unused views (forever).
DROP VIEW SourcePackagePublishing;
DROP VIEW BinaryPackagePublishing;

-- Remove-for-editing
DROP VIEW SourcePackagePublishingHistory;
DROP VIEW BinaryPackagePublishingHistory;


-- Create new table depending only on SecureSourcePackagePublishingHistory.
CREATE VIEW sourcepackagefilepublishing AS
    SELECT
      (((libraryfilealias.id)::text || '.'::text) || (securesourcepackagepublishinghistory.id)::text) AS id,
      distrorelease.distribution,
      securesourcepackagepublishinghistory.id AS sourcepackagepublishing,
      sourcepackagereleasefile.libraryfile AS libraryfilealias,
      libraryfilealias.filename AS libraryfilealiasfilename,
      sourcepackagename.name AS sourcepackagename,
      component.name AS componentname,
      distrorelease.name AS distroreleasename,
      securesourcepackagepublishinghistory.status AS publishingstatus,
      securesourcepackagepublishinghistory.pocket,
      securesourcepackagepublishinghistory.archive
    FROM
      ((((((securesourcepackagepublishinghistory
      JOIN sourcepackagerelease ON ((securesourcepackagepublishinghistory.sourcepackagerelease = sourcepackagerelease.id)))
      JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)))
      JOIN sourcepackagereleasefile ON ((sourcepackagereleasefile.sourcepackagerelease = sourcepackagerelease.id)))
      JOIN libraryfilealias ON ((libraryfilealias.id = sourcepackagereleasefile.libraryfile)))
      JOIN distrorelease ON ((securesourcepackagepublishinghistory.distrorelease = distrorelease.id)))
      JOIN component ON ((securesourcepackagepublishinghistory.component = component.id)))
    WHERE
      securesourcepackagepublishinghistory.dateremoved is NULL;

-- Deriving directly from SBPPH.
CREATE VIEW binarypackagefilepublishing AS
    SELECT
      (((libraryfilealias.id)::text || '.'::text) || (securebinarypackagepublishinghistory.id)::text) AS id,
      distrorelease.distribution,
      securebinarypackagepublishinghistory.id AS binarypackagepublishing,
      component.name AS componentname,
      libraryfilealias.filename AS libraryfilealiasfilename,
      sourcepackagename.name AS sourcepackagename,
      binarypackagefile.libraryfile AS libraryfilealias,
      distrorelease.name AS distroreleasename,
      distroarchrelease.architecturetag,
      securebinarypackagepublishinghistory.status AS publishingstatus,
      securebinarypackagepublishinghistory.pocket,
      securebinarypackagepublishinghistory.archive
    FROM
      (((((((((securebinarypackagepublishinghistory
      JOIN binarypackagerelease ON ((securebinarypackagepublishinghistory.binarypackagerelease = binarypackagerelease.id)))
      JOIN build ON ((binarypackagerelease.build = build.id)))
      JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id)))
      JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)))
      JOIN binarypackagefile ON ((binarypackagefile.binarypackagerelease = binarypackagerelease.id)))
      JOIN libraryfilealias ON ((binarypackagefile.libraryfile = libraryfilealias.id)))
      JOIN distroarchrelease ON ((securebinarypackagepublishinghistory.distroarchrelease = distroarchrelease.id)))
      JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id)))
      JOIN component ON ((securebinarypackagepublishinghistory.component = component.id)))
    WHERE
      securebinarypackagepublishinghistory.dateremoved is NULL;

-- Proper name, adding 'archive' column, deriving directly from SBPPH.
CREATE VIEW publishedpackage AS
    SELECT
      securebinarypackagepublishinghistory.id,
      distroarchrelease.id AS distroarchrelease,
      distrorelease.distribution,
      distrorelease.id AS distrorelease,
      distrorelease.name AS distroreleasename,
      processorfamily.id AS processorfamily,
      processorfamily.name AS processorfamilyname,
      securebinarypackagepublishinghistory.status AS packagepublishingstatus,
      component.name AS component,
      section.name AS section,
      binarypackagerelease.id AS binarypackagerelease,
      binarypackagename.name AS binarypackagename,
      binarypackagerelease.summary AS binarypackagesummary,
      binarypackagerelease.description AS binarypackagedescription,
      binarypackagerelease.version AS binarypackageversion,
      build.id AS build,
      build.datebuilt,
      sourcepackagerelease.id AS sourcepackagerelease,
      sourcepackagerelease.version AS sourcepackagereleaseversion,
      sourcepackagename.name AS sourcepackagename,
      securebinarypackagepublishinghistory.pocket,
      securebinarypackagepublishinghistory.archive,
      binarypackagerelease.fti AS binarypackagefti
    FROM
      ((((((((((securebinarypackagepublishinghistory
      JOIN distroarchrelease ON ((distroarchrelease.id = securebinarypackagepublishinghistory.distroarchrelease)))
      JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id)))
      JOIN processorfamily ON ((distroarchrelease.processorfamily = processorfamily.id)))
      JOIN component ON ((securebinarypackagepublishinghistory.component = component.id)))
      JOIN binarypackagerelease ON ((securebinarypackagepublishinghistory.binarypackagerelease = binarypackagerelease.id)))
      JOIN section ON ((securebinarypackagepublishinghistory.section = section.id)))
      JOIN binarypackagename ON ((binarypackagerelease.binarypackagename = binarypackagename.id)))
      JOIN build ON ((binarypackagerelease.build = build.id)))
      JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id)))
      JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)))
    WHERE
      securebinarypackagepublishinghistory.dateremoved is NULL;

-- Aggregating 'removed_by' & 'removal_comment' to 1st stage publishing views.
CREATE VIEW sourcepackagepublishinghistory AS
    SELECT 
      securesourcepackagepublishinghistory.id,
      securesourcepackagepublishinghistory.sourcepackagerelease,
      securesourcepackagepublishinghistory.status,
      securesourcepackagepublishinghistory.component,
      securesourcepackagepublishinghistory.section,
      securesourcepackagepublishinghistory.distrorelease,
      securesourcepackagepublishinghistory.pocket,
      securesourcepackagepublishinghistory.archive,
      securesourcepackagepublishinghistory.datecreated,
      securesourcepackagepublishinghistory.datepublished,
      securesourcepackagepublishinghistory.datesuperseded,
      securesourcepackagepublishinghistory.supersededby,
      securesourcepackagepublishinghistory.datemadepending,
      securesourcepackagepublishinghistory.scheduleddeletiondate,
      securesourcepackagepublishinghistory.dateremoved,
      securesourcepackagepublishinghistory.removed_by,
      securesourcepackagepublishinghistory.removal_comment,
      securesourcepackagepublishinghistory.embargo,
      securesourcepackagepublishinghistory.embargolifted
    FROM securesourcepackagepublishinghistory
    WHERE securesourcepackagepublishinghistory.embargo = false;

CREATE VIEW binarypackagepublishinghistory AS
    SELECT 
      securebinarypackagepublishinghistory.id,
      securebinarypackagepublishinghistory.binarypackagerelease,
      securebinarypackagepublishinghistory.status,
      securebinarypackagepublishinghistory.component,
      securebinarypackagepublishinghistory.section,
      securebinarypackagepublishinghistory.priority,
      securebinarypackagepublishinghistory.distroarchrelease,
      securebinarypackagepublishinghistory.pocket,
      securebinarypackagepublishinghistory.archive,
      securebinarypackagepublishinghistory.datecreated,
      securebinarypackagepublishinghistory.datepublished,
      securebinarypackagepublishinghistory.datesuperseded,
      securebinarypackagepublishinghistory.supersededby,
      securebinarypackagepublishinghistory.datemadepending,
      securebinarypackagepublishinghistory.scheduleddeletiondate,
      securebinarypackagepublishinghistory.dateremoved,
      securebinarypackagepublishinghistory.removed_by,
      securebinarypackagepublishinghistory.removal_comment,
      securebinarypackagepublishinghistory.embargo,
      securebinarypackagepublishinghistory.embargolifted
    FROM securebinarypackagepublishinghistory
    WHERE securebinarypackagepublishinghistory.embargo = false;


-- Updating old records to match the current state machine:
-- 6: PENDINGREMOVAL
-- 7: REMOVED
-- turned into:
-- 3: SUPERSEDED

UPDATE SecureSourcePackagePublishingHistory
    SET status = 3
    WHERE status IN (6, 7);

UPDATE SecureBinaryPackagePublishingHistory
    SET status = 3
    WHERE status IN (6, 7);


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 54, 0);
