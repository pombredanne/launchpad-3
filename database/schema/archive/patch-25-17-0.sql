-- Quieten things down...
SET client_min_messages=ERROR;

/*
 * First up, get rid of the vestigal and obsolete osfile and osfileinpackage
 * tables which were originally going to describe the contents of binary
 * packages, but let's face it, they'd get too big and too scary so we get
 * rid of 'em
 */

DROP TABLE osfileinpackage;
DROP TABLE osfile;

/*
 * Perform table renames
 *
 *  T: BinaryPackage                  -> BinaryPackageRelease
 */
ALTER TABLE BinaryPackage RENAME TO BinaryPackageRelease;
ALTER TABLE binarypackage_id_seq RENAME TO binarypackagerelease_id_seq;
ALTER TABLE BinaryPackageRelease ALTER COLUMN id
      SET DEFAULT nextval('public.binarypackagerelease_id_seq'::text);
-- Indexes
ALTER TABLE binarypackage_pkey
    RENAME TO binarypackagerelease_pkey;
ALTER TABLE binarypackage_fti
    RENAME TO binarypackagerelease_fti;
ALTER TABLE binarypackage_version_idx
    RENAME TO binarypackagerelease_version_idx;
ALTER TABLE binarypackage_build_idx
    RENAME TO binarypackagerelease_build_idx;
-- Constraints
ALTER TABLE BinaryPackageRelease
    DROP CONSTRAINT binarypackage_binarypackagename_fk;
ALTER TABLE BinaryPackageRelease
    ADD CONSTRAINT binarypackagerelease_binarypackagename_fk
    FOREIGN KEY (binarypackagename) REFERENCES BinaryPackageName;
ALTER TABLE BinaryPackageRelease
    DROP CONSTRAINT binarypackage_binarypackagename_key;
ALTER TABLE BinaryPackageRelease
    ADD CONSTRAINT binarypackagerelease_binarypackagename_key
    UNIQUE (binarypackagename, build, version);
ALTER TABLE BinaryPackageRelease
    DROP CONSTRAINT binarypackage_section_fk;
ALTER TABLE BinaryPackageRelease
    ADD CONSTRAINT binarypackagerelease_section_fk
    FOREIGN KEY (section) REFERENCES Section;
ALTER TABLE BinaryPackageRelease
    DROP CONSTRAINT binarypackage_component_fk;
ALTER TABLE BinaryPackageRelease
    ADD CONSTRAINT binarypackagerelease_component_fk
    FOREIGN KEY (component) REFERENCES Component;
ALTER TABLE BinaryPackageRelease
    DROP CONSTRAINT binarypackage_build_fk;
ALTER TABLE BinaryPackageRelease
    ADD CONSTRAINT binarypackagerelease_build_fk
    FOREIGN KEY (build) REFERENCES Build;
/*
 *  T: SourcePackagePublishingHistory -> SecureSourcePackagePublishingHistory
 */
ALTER TABLE SourcePackagePublishingHistory
    RENAME TO SecureSourcePackagePublishingHistory;
ALTER TABLE sourcepackagepublishinghistory_id_seq 
    RENAME TO securesourcepackagepublishinghistory_id_seq;
ALTER TABLE SecureSourcePackagePublishingHistory ALTER COLUMN id SET DEFAULT 
      nextval('public.securesourcepackagepublishinghistory_id_seq'::text);
-- Indexes
ALTER TABLE sourcepackagepublishinghistory_pkey
    RENAME TO securesourcepackagepublishinghistory_pkey;
ALTER TABLE sourcepackagepublishinghistory_distrorelease_key
    RENAME TO securesourcepackagepublishinghistory_distrorelease_idx;
ALTER TABLE sourcepackagepublishinghistory_pocket_idx
    RENAME TO securesourcepackagepublishinghistory_pocket_idx;
ALTER TABLE sourcepackagepublishinghistory_sourcepackagerelease_key
    RENAME TO securesourcepackagepublishinghistory_sourcepackagerelease_idx;
ALTER TABLE sourcepackagepublishinghistory_status_key
    RENAME TO securesourcepackagepublishinghistory_status_idx;
CREATE INDEX securesourcepackagepublishinghistory_section_idx
    ON SecureSourcePackagePublishingHistory(section);
CREATE INDEX securesourcepackagepublishinghistory_component_idx
    ON SecureSourcePackagePublishingHistory(component);
-- Constraints
ALTER TABLE SecureSourcePackagePublishingHistory
    DROP CONSTRAINT sourcepackagepublishinghistory_supersededby_fk;
ALTER TABLE SecureSourcePackagePublishingHistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_supersededby_fk
    FOREIGN KEY (supersededby) REFERENCES SourcePackageRelease;
ALTER TABLE SecureSourcePackagePublishingHistory
    DROP CONSTRAINT sourcepackagepublishinghistory_section_fk;
ALTER TABLE SecureSourcePackagePublishingHistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_section_fk
    FOREIGN KEY (section) REFERENCES Section;
ALTER TABLE SecureSourcePackagePublishingHistory
    DROP CONSTRAINT sourcepackagepublishinghistory_component_fk;
ALTER TABLE SecureSourcePackagePublishingHistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_component_fk
    FOREIGN KEY (component) REFERENCES Component;
ALTER TABLE SecureSourcePackagePublishingHistory
    DROP CONSTRAINT sourcepackagepublishinghistory_distrorelease_fk;
ALTER TABLE SecureSourcePackagePublishingHistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_distrorelease_fk
    FOREIGN KEY (distrorelease) REFERENCES DistroRelease;
ALTER TABLE SecureSourcePackagePublishingHistory
    DROP CONSTRAINT sourcepackagepublishinghistory_sourcepackagerelease_fk;
ALTER TABLE SecureSourcePackagePublishingHistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_sourcepackagerelease_fk
    FOREIGN KEY (sourcepackagerelease) REFERENCES SourcePackageRelease;

/*
 *  T: PackagePublishingHistory       -> SecureBinaryPackagePublishingHistory
 */
ALTER TABLE PackagePublishingHistory
    RENAME TO SecureBinaryPackagePublishingHistory;
ALTER TABLE packagepublishinghistory_id_seq 
    RENAME TO securebinarypackagepublishinghistory_id_seq;
ALTER TABLE SecureBinaryPackagePublishingHistory ALTER COLUMN id SET DEFAULT 
      nextval('public.securebinarypackagepublishinghistory_id_seq'::text);
-- Columns
ALTER TABLE SecureBinaryPackagePublishingHistory
    RENAME COLUMN binarypackage TO binarypackagerelease;
-- Indexes
ALTER TABLE packagepublishinghistory_pkey
    RENAME TO securebinarypackagepublishinghistory_pkey;
ALTER TABLE packagepublishinghistory_binarypackage_key
    RENAME TO securebinarypackagepublishinghistory_binarypackagerelease_idx;
ALTER TABLE packagepublishinghistory_component_key
    RENAME TO securebinarypackagepublishinghistory_component_idx;
ALTER TABLE packagepublishinghistory_distroarchrelease_key
    RENAME TO securebinarypackagepublishinghistory_distroarchrelease_idx;
ALTER TABLE packagepublishinghistory_pocket_idx
    RENAME TO securebinarypackagepublishinghistory_pocket_idx;
ALTER TABLE packagepublishinghistory_section_key
    RENAME TO securebinarypackagepublishinghistory_section_idx;
ALTER TABLE packagepublishinghistory_status_key
    RENAME TO securebinarypackagepublishinghistory_status_idx;
-- Constraints
ALTER TABLE SecureBinaryPackagePublishingHistory
    DROP CONSTRAINT packagepublishinghistory_supersededby_fk;
ALTER TABLE SecureBinaryPackagePublishingHistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_supersededby_fk
    FOREIGN KEY (supersededby) REFERENCES Build;
ALTER TABLE SecureBinaryPackagePublishingHistory
    DROP CONSTRAINT sourcepackagepublishinghistory_section_fk;
ALTER TABLE SecureBinaryPackagePublishingHistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_section_fk
    FOREIGN KEY (section) REFERENCES Section;
ALTER TABLE SecureBinaryPackagePublishingHistory
    DROP CONSTRAINT sourcepackagepublishinghistory_component_fk;
ALTER TABLE SecureBinaryPackagePublishingHistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_component_fk
    FOREIGN KEY (component) REFERENCES Component;
ALTER TABLE SecureBinaryPackagePublishingHistory
    DROP CONSTRAINT packagepublishinghistory_distroarchrelease_fk;
ALTER TABLE SecureBinaryPackagePublishingHistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_distroarchrelease_fk
    FOREIGN KEY (distroarchrelease) REFERENCES DistroArchRelease;
ALTER TABLE SecureBinaryPackagePublishingHistory
    DROP CONSTRAINT packagepublishinghistory_binarypackage_fk;
ALTER TABLE SecureBinaryPackagePublishingHistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_binarypackagerelease_fk
    FOREIGN KEY (binarypackagerelease) REFERENCES BinaryPackageRelease;

/* Refactor BinaryPackageFile */
ALTER TABLE BinaryPackageFile
    RENAME COLUMN binarypackage TO binarypackagerelease;
ALTER TABLE BinaryPackageFile
    DROP CONSTRAINT binarypackagefile_binarypackage_fk;
ALTER TABLE BinaryPackageFile
    ADD CONSTRAINT binarypackagefile_binarypackagerelease_fk
    FOREIGN KEY(binarypackagerelease) REFERENCES BinaryPackageRelease;


/*
 * Catch the changes in the following views and update them:
 *
 *  PackagePublishingPublicHistory (Rename to BinaryPackagePublishingHistory)
 *  PackagePublishing (Rename to BinaryPackagePublishing, Reparent to
 *                                            BinaryPackagePublishingHistory)
 *  SourcePackagePublishing (Reparent onto SourcePackagePublishingHistory)
 *  SourcePackagePublishingPublicHistory 
 *                          (Rename to SourcePackagePublishingHistory)
 *  BinaryPackageFilePublishing (Reparent onto BinaryPackageRelease and
 *                               BinaryPackagePublishing)
 *  SourcePackageFilePublishing (Simple update)
 *  PublishedPackageView (Rename to PublishingBinaryPackageView, add pocket)
 *  SourcePackagePublishingView (Simple update, add pocket)
 *  BinaryPackagePublishingView (Reparent, update, add pocket)
 *  VSourcePackageReleasePublishing (Simple update, add pocket)
 *  VSourcePackageInDistro (Simple update, add pocket)
 *
 * Implications in code:
 *
 *  The renames will involve code changes to catch the new names. If any of
 *  the views involve (the somewhat dubious practice of) inheritance of sql
 *  objects then those views may need updating a little more.
 *
 *  Each application will need checking, all the imports need checking because
 *  name changes will imply code changes in many places.
 */

-- 1. Drop all the views

DROP VIEW PackagePublishingPublicHistory;
DROP VIEW PublishedPackageView;
DROP VIEW BinaryPackageFilePublishing;
DROP VIEW BinaryPackagePublishingView;
DROP VIEW PackagePublishing;
DROP VIEW SourcePackagePublishingPublicHistory;
DROP VIEW SourcePackageFilePublishing;
DROP VIEW SourcePackagePublishingView;
DROP VIEW VSourcePackageInDistro;
DROP VIEW VSourcePackageReleasePublishing;
DROP VIEW SourcePackagePublishing;


--
-- Current situation is as follows:
--
-- T: BinaryPackageRelease
-- T: SecureBinaryPackagePublishingHistory
-- T: SecureSourcePackagePublishingHistory
--

--
-- First up are the direct publishing views...
--

CREATE VIEW SourcePackagePublishingHistory AS
SELECT * FROM SecureSourcePackagePublishingHistory 
WHERE embargo = FALSE;

CREATE VIEW SourcePackagePublishing AS
SELECT * FROM SourcePackagePublishingHistory
WHERE status < 7; -- dbschema.PackagePublishingStatus.REMOVED

CREATE VIEW BinaryPackagePublishingHistory AS
SELECT * FROM SecureBinaryPackagePublishingHistory 
WHERE embargo = FALSE;

CREATE VIEW BinaryPackagePublishing AS
SELECT * FROM BinaryPackagePublishingHistory
WHERE status < 7; -- dbschema.PackagePublishingStatus.REMOVED

-- Four down, Seven to go...

-- This is as the database reports it, with packagepublishing ->
-- binarypackagepublishing and pocket added for good measure.
-- All right-hand names left unchanged except for 
-- binarypackage->binarypackagerelease

CREATE VIEW PublishedPackageView AS
SELECT binarypackagepublishing.id AS id, 
       distroarchrelease.id AS distroarchrelease, 
       distrorelease.distribution, 
       distrorelease.id AS distrorelease, 
       distrorelease.name AS distroreleasename,
       processorfamily.id AS processorfamily, 
       processorfamily.name AS processorfamilyname, 
       binarypackagepublishing.status AS packagepublishingstatus, 
       component.name AS component, 
       section.name AS section, 
       binarypackagerelease.id AS binarypackagerelease, 
       binarypackagename.name AS binarypackagename, 
       binarypackagerelease.summary AS binarypackagesummary,
       binarypackagerelease.description AS binarypackagedescription,
       binarypackagerelease."version" AS binarypackageversion, 
       build.id AS build,
       build.datebuilt, 
       sourcepackagerelease.id AS sourcepackagerelease,
       sourcepackagerelease."version" AS sourcepackagereleaseversion,
       sourcepackagename.name AS sourcepackagename,
       binarypackagepublishing.pocket AS pocket,
       binarypackagerelease.fti AS binarypackagefti
       
  FROM binarypackagepublishing
  JOIN distroarchrelease ON 
       distroarchrelease.id = binarypackagepublishing.distroarchrelease
  JOIN distrorelease ON 
       distroarchrelease.distrorelease = distrorelease.id
  JOIN processorfamily ON 
       distroarchrelease.processorfamily = processorfamily.id
  JOIN component ON binarypackagepublishing.component = component.id
  JOIN binarypackagerelease ON 
       binarypackagepublishing.binarypackagerelease = binarypackagerelease.id
  JOIN section ON binarypackagepublishing.section = section.id
  JOIN binarypackagename ON 
       binarypackagerelease.binarypackagename = binarypackagename.id
  JOIN build ON binarypackagerelease.build = build.id
  JOIN sourcepackagerelease ON 
       build.sourcepackagerelease = sourcepackagerelease.id
  JOIN sourcepackagename ON 
       sourcepackagerelease.sourcepackagename = sourcepackagename.id
;

-- This is as the database reports, with packagepublishing changed to
-- binarypackagepublishing, including on the right hand side.

CREATE VIEW BinaryPackageFilePublishing AS
SELECT (libraryfilealias.id::text || '.'::text) || 
	binarypackagepublishing.id::text AS id, 
       distrorelease.distribution, 
       binarypackagepublishing.id AS binarypackagepublishing, 
       component.name AS componentname, 
       libraryfilealias.filename AS libraryfilealiasfilename, 
       sourcepackagename.name AS sourcepackagename, 
       binarypackagefile.libraryfile AS libraryfilealias, 
       distrorelease.name AS distroreleasename, 
       distroarchrelease.architecturetag, 
       binarypackagepublishing.status AS publishingstatus, 
       binarypackagepublishing.pocket

  FROM binarypackagepublishing
  JOIN binarypackagerelease ON 
       binarypackagepublishing.binarypackagerelease = binarypackagerelease.id
  JOIN build ON binarypackagerelease.build = build.id
  JOIN sourcepackagerelease ON 
       build.sourcepackagerelease = sourcepackagerelease.id
  JOIN sourcepackagename ON 
       sourcepackagerelease.sourcepackagename = sourcepackagename.id
  JOIN binarypackagefile ON 
       binarypackagefile.binarypackagerelease = binarypackagerelease.id
  JOIN libraryfilealias ON binarypackagefile.libraryfile = libraryfilealias.id
  JOIN distroarchrelease ON 
       binarypackagepublishing.distroarchrelease = distroarchrelease.id
  JOIN distrorelease ON distroarchrelease.distrorelease = distrorelease.id
  JOIN component ON binarypackagepublishing.component = component.id
;


-- As per the DB again, updated to binarypackagepublishing and added pocket
CREATE VIEW BinaryPackagePublishingView AS
SELECT binarypackagepublishing.id, 
       distrorelease.name AS distroreleasename, 
       binarypackagename.name AS binarypackagename, 
       component.name AS componentname, 
       section.name AS sectionname, 
       binarypackagepublishing.priority, 
       distrorelease.distribution, 
       binarypackagepublishing.status AS publishingstatus,
       binarypackagepublishing.pocket
  FROM binarypackagepublishing, 
       distrorelease, 
       distroarchrelease, 
       binarypackagerelease, 
       binarypackagename, 
       component, 
       section
 WHERE binarypackagepublishing.distroarchrelease = distroarchrelease.id 
   AND distroarchrelease.distrorelease = distrorelease.id 
   AND binarypackagepublishing.binarypackagerelease = binarypackagerelease.id 
   AND binarypackagerelease.binarypackagename = binarypackagename.id 
   AND binarypackagepublishing.component = component.id 
   AND binarypackagepublishing.section = section.id
;


-- Since the source package publishing stuff has hardly changed (names) this
-- is identical to the database dump
CREATE VIEW SourcePackageFilePublishing	AS
SELECT (libraryfilealias.id::text || '.'::text) || 
	sourcepackagepublishing.id::text AS id, 
       distrorelease.distribution, 
       sourcepackagepublishing.id AS sourcepackagepublishing, 
       sourcepackagereleasefile.libraryfile AS libraryfilealias, 
       libraryfilealias.filename AS libraryfilealiasfilename, 
       sourcepackagename.name AS sourcepackagename, 
       component.name AS componentname, 
       distrorelease.name AS distroreleasename, 
       sourcepackagepublishing.status AS publishingstatus, 
       sourcepackagepublishing.pocket
  FROM sourcepackagepublishing
  JOIN sourcepackagerelease ON 
       sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id
  JOIN sourcepackagename ON 
       sourcepackagerelease.sourcepackagename = sourcepackagename.id
  JOIN sourcepackagereleasefile ON 
       sourcepackagereleasefile.sourcepackagerelease = sourcepackagerelease.id
  JOIN libraryfilealias ON 
       libraryfilealias.id = sourcepackagereleasefile.libraryfile
  JOIN distrorelease ON 
       sourcepackagepublishing.distrorelease = distrorelease.id
  JOIN component ON sourcepackagepublishing.component = component.id
;

-- Again, since the names are unchanged, this is a direct dump from the DB
-- but with pocket added for good measure.
CREATE VIEW SourcePackagePublishingView AS
SELECT sourcepackagepublishing.id, 
       distrorelease.name AS distroreleasename, 
       sourcepackagename.name AS sourcepackagename, 
       component.name AS componentname, 
       section.name AS sectionname, 
       distrorelease.distribution, 
       sourcepackagepublishing.status AS publishingstatus,
       sourcepackagepublishing.pocket AS pocket
       
  FROM sourcepackagepublishing
  JOIN distrorelease ON 
       sourcepackagepublishing.distrorelease = distrorelease.id
  JOIN sourcepackagerelease ON 
       sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id
  JOIN sourcepackagename ON 
       sourcepackagerelease.sourcepackagename = sourcepackagename.id
  JOIN component ON sourcepackagepublishing.component = component.id
  JOIN section ON sourcepackagepublishing.section = section.id
;

-- VSourcePackageInDistro turns out to be very simple and unchanged
CREATE VIEW VSourcePackageInDistro AS
SELECT sourcepackagerelease.id, 
       sourcepackagerelease.manifest, 
       sourcepackagerelease.format, 
       sourcepackagerelease.sourcepackagename, 
       sourcepackagename.name, 
       sourcepackagepublishing.distrorelease, 
       distrorelease.distribution,
       sourcepackagepublishing.pocket,
       sourcepackagepublishing.status
  FROM sourcepackagepublishing
  JOIN sourcepackagerelease ON 
       sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id
  JOIN distrorelease ON 
       sourcepackagepublishing.distrorelease = distrorelease.id
  JOIN sourcepackagename ON 
       sourcepackagerelease.sourcepackagename = sourcepackagename.id
;


-- This is not a simple view, I'm not convinced about it, it's verbatim here
CREATE VIEW VSourcePackageReleasePublishing AS
SELECT DISTINCT 
       sourcepackagerelease.id, 
       sourcepackagename.name, 
       maintainership.maintainer, 
       sourcepackagepublishing.status AS publishingstatus, 
       sourcepackagepublishing.datepublished, 
       sourcepackagepublishing.distrorelease, 
       component.name AS componentname, 
       sourcepackagerelease.architecturehintlist, 
       sourcepackagerelease."version", 
       sourcepackagerelease.creator, 
       sourcepackagerelease.format, 
       sourcepackagerelease.manifest, 
       sourcepackagerelease.section, 
       sourcepackagerelease.component, 
       sourcepackagerelease.changelog, 
       sourcepackagerelease.builddepends, 
       sourcepackagerelease.builddependsindep, 
       sourcepackagerelease.urgency, 
       sourcepackagerelease.dateuploaded, 
       sourcepackagerelease.dsc, 
       sourcepackagerelease.dscsigningkey, 
       sourcepackagerelease.uploaddistrorelease, 
       sourcepackagerelease.sourcepackagename
  FROM sourcepackagepublishing
  JOIN sourcepackagerelease ON 
       sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id
  JOIN sourcepackagename ON 
       sourcepackagerelease.sourcepackagename = sourcepackagename.id
  JOIN distrorelease ON 
       sourcepackagepublishing.distrorelease = distrorelease.id
  JOIN component ON sourcepackagepublishing.component = component.id
  LEFT JOIN maintainership ON 
       sourcepackagerelease.sourcepackagename = maintainership.sourcepackagename
   AND distrorelease.distribution = maintainership.distribution
ORDER BY sourcepackagerelease.id, sourcepackagename.name, maintainership.maintainer, sourcepackagepublishing.status, sourcepackagepublishing.datepublished, sourcepackagepublishing.distrorelease, component.name, sourcepackagerelease.architecturehintlist, sourcepackagerelease."version", sourcepackagerelease.creator, sourcepackagerelease.format, sourcepackagerelease.manifest, sourcepackagerelease.section, sourcepackagerelease.component, sourcepackagerelease.changelog, sourcepackagerelease.builddepends, sourcepackagerelease.builddependsindep, sourcepackagerelease.urgency, sourcepackagerelease.dateuploaded, sourcepackagerelease.dsc, sourcepackagerelease.dscsigningkey, sourcepackagerelease.uploaddistrorelease, sourcepackagerelease.sourcepackagename;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,17,0);
