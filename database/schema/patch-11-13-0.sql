SET client_min_messages=ERROR;

-- clean up distrorelease status

ALTER TABLE DistroRelease RENAME COLUMN ReleaseState TO ReleaseStatus;

/* Create Maintainership Table */

CREATE TABLE Maintainership (
    id                  serial PRIMARY KEY,
    distribution        integer NOT NULL
                        CONSTRAINT maintainership_distribution_fk
                        REFERENCES Distribution(id),
    sourcepackagename   integer NOT NULL
                        CONSTRAINT maintainership_sourcepackagename_fk
                        REFERENCES SourcePackageName(id),
    maintainer          integer NOT NULL
                        CONSTRAINT maintainership_maintainer_fk
                        REFERENCES Person(id)
);

 -- migrate data from SourcePackage to Maintainership table
INSERT INTO Maintainership (distribution, sourcepackagename, maintainer)
    SELECT distro, sourcepackagename, maintainer
    FROM SourcePackage;

/* Packaging */

ALTER TABLE Packaging ADD COLUMN sourcepackagename INTEGER;
ALTER TABLE Packaging ADD CONSTRAINT packaging_sourcepackagename_fk
      FOREIGN KEY (sourcepackagename) REFERENCES SourcePackagename(id);

ALTER TABLE Packaging ADD COLUMN distrorelease INTEGER;
ALTER TABLE Packaging ADD CONSTRAINT packaging_distrorelease_fk
      FOREIGN KEY (distrorelease) REFERENCES DistroRelease(id);

-- data migration
UPDATE Packaging SET sourcepackagename=sourcepackage.sourcepackagename
    FROM SourcePackage WHERE packaging.sourcepackage=SourcePackage.id;
UPDATE Packaging
    SET distrorelease=(SELECT id FROM DistroRelease WHERE name='hoary');
ALTER TABLE packaging DROP COLUMN sourcepackage;


/* SourcePackageRelease */

ALTER TABLE SourcePackageRelease ADD COLUMN uploaddistrorelease INTEGER ;
ALTER TABLE SourcePackageRelease ADD CONSTRAINT 
    sourcepackagerelease_uploaddistrorelease_fk
          FOREIGN KEY (uploaddistrorelease) REFERENCES DistroRelease(id);
ALTER TABLE SourcePackageRelease ADD COLUMN format INTEGER;

-- migrate the format data from SourcePackage to SourcePackageRelease
UPDATE SourcePackageRelease SET format = SourcePackage.srcpackageformat FROM
SourcePackage WHERE SourcePackageRelease.sourcepackage = SourcePackage.id;
ALTER TABLE SourcePackageRelease ALTER COLUMN format SET NOT NULL;

-- set uploaddistrorelease to hoary as a best guess for now
UPDATE SourcePackageRelease
    SET uploaddistrorelease=(SELECT id FROM DistroRelease WHERE name='hoary');
ALTER TABLE SourcePackageRelease ALTER COLUMN uploaddistrorelease SET NOT NULL;

/* SourceSource */

ALTER TABLE SourceSource ADD COLUMN sourcepackagename INTEGER;
ALTER TABLE SourceSource ADD CONSTRAINT sourcesource_sourcepackagename_fk
      FOREIGN KEY (sourcepackagename) REFERENCES SourcePackagename(id);

ALTER TABLE SourceSource ADD COLUMN distrorelease INTEGER;
ALTER TABLE SourceSource ADD CONSTRAINT sourcesource_distrorelease_fk
      FOREIGN KEY (distrorelease) REFERENCES DistroRelease(id);

-- Refactor SourceSource to do without SourcePackage
UPDATE SourceSource
    SET sourcepackagename=SourcePackage.sourcepackagename
    FROM SourcePackage WHERE SourceSource.sourcepackage = SourcePackage.id;
UPDATE SourceSource
    SET distrorelease=(SELECT id FROM DistroRelease WHERE name='hoary')
    WHERE SourceSource.sourcepackage IS NOT NULL;
ALTER TABLE SourceSource DROP COLUMN sourcepackage;


-- Alter Views

-- VSourcePackageInDistro

-- No ALTER VIEW, so DROP and ADD

DROP VIEW vsourcepackageindistro;

CREATE VIEW vsourcepackageindistro AS
    SELECT
        sourcepackagerelease.id, 
        sourcepackagerelease.manifest, 
        sourcepackagerelease.format, 
        sourcepackagerelease.sourcepackagename, 
        sourcepackagename.name,
        sourcepackagepublishing.distrorelease,
        distrorelease.distribution
    FROM
        sourcepackagepublishing
    INNER JOIN
        sourcepackagerelease ON 
            sourcepackagepublishing.sourcepackagerelease = 
            sourcepackagerelease.id 
    INNER JOIN
         distrorelease ON
            sourcepackagepublishing.distrorelease = distrorelease.id
    INNER JOIN
         sourcepackagename ON
            sourcepackagerelease.sourcepackagename = sourcepackagename.id
    ;

-- VSourcePackageReleasePublishing
-- no ALTER VIEW, so DROP and ADD

DROP VIEW vsourcepackagereleasepublishing;

CREATE VIEW vsourcepackagereleasepublishing AS
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
    FROM 
    sourcepackagepublishing
    INNER JOIN
        sourcepackagerelease ON
            sourcepackagepublishing.sourcepackagerelease =
            sourcepackagerelease.id
    INNER JOIN 
        sourcepackagename ON
            sourcepackagerelease.sourcepackagename=sourcepackagename.id
    INNER JOIN
        distrorelease ON
            sourcepackagepublishing.distrorelease = distrorelease.id
    INNER JOIN
        component ON
            sourcepackagepublishing.component = component.id
    LEFT OUTER JOIN
        maintainership ON 
            sourcepackagerelease.sourcepackagename = 
                maintainership.sourcepackagename AND
            distrorelease.distribution = maintainership.distribution
    ;


-- PublishedPackageView

DROP VIEW publishedpackageview;

CREATE VIEW publishedpackageview AS
    SELECT 
        packagepublishing.id, 
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
        binarypackage.shortdesc AS binarypackageshortdesc, 
        binarypackage.description AS binarypackagedescription, 
        binarypackage."version" AS binarypackageversion, 
        build.id AS build, 
        build.datebuilt, 
        sourcepackagerelease.id AS sourcepackagerelease, 
        sourcepackagerelease."version" AS sourcepackagereleaseversion, 
        sourcepackagename.name AS sourcepackagename, 
        binarypackage.fti AS binarypackagefti 
    FROM 
    packagepublishing
    INNER JOIN 
        distroarchrelease ON
            distroarchrelease.id = packagepublishing.distroarchrelease
    INNER JOIN
        distrorelease ON
            distroarchrelease.distrorelease = distrorelease.id
    INNER JOIN
        processorfamily ON
            distroarchrelease.processorfamily = processorfamily.id
    INNER JOIN
        component ON
            packagepublishing.component = component.id
    INNER JOIN
        binarypackage ON
            packagepublishing.binarypackage = binarypackage.id
    INNER JOIN
        section ON
            packagepublishing.section = section.id
    INNER JOIN
        binarypackagename ON
            binarypackage.binarypackagename = binarypackagename.id
    INNER JOIN
        build ON
            binarypackage.build = build.id
    INNER JOIN
        sourcepackagerelease ON
            build.sourcepackagerelease = sourcepackagerelease.id
    INNER JOIN
        sourcepackagename ON
            sourcepackagerelease.sourcepackagename = sourcepackagename.id
    ;

-- SourcePackagePublishingView

DROP VIEW sourcepackagepublishingview;

CREATE VIEW sourcepackagepublishingview AS
    SELECT 
        sourcepackagepublishing.id, 
        distrorelease.name AS distroreleasename, 
        sourcepackagename.name AS sourcepackagename, 
        component.name AS componentname, 
        section.name AS sectionname, 
        distrorelease.distribution, 
        sourcepackagepublishing.status AS publishingstatus 
    FROM 
    sourcepackagepublishing
    INNER JOIN
        distrorelease ON 
            sourcepackagepublishing.distrorelease = distrorelease.id
    INNER JOIN
        sourcepackagerelease ON
            sourcepackagepublishing.sourcepackagerelease =
            sourcepackagerelease.id
    INNER JOIN
        sourcepackagename ON
            sourcepackagerelease.sourcepackagename = sourcepackagename.id
    INNER JOIN
        component ON
            sourcepackagepublishing.component = component.id
    INNER JOIN
        section ON
            sourcepackagepublishing.section = section.id
    ;

-- BinaryPackageFilePublishing

DROP VIEW binarypackagefilepublishing;

CREATE VIEW binarypackagefilepublishing AS
    SELECT 
        (((libraryfilealias.id)::text || '.'::text) || (packagepublishing.id)::text) AS id, 
        distrorelease.distribution, 
        packagepublishing.id AS packagepublishing, 
        component.name AS componentname, 
        libraryfilealias.filename AS libraryfilealiasfilename, 
        sourcepackagename.name AS sourcepackagename, 
        binarypackagefile.libraryfile AS libraryfilealias, 
        distrorelease.name AS distroreleasename, 
        distroarchrelease.architecturetag, 
        packagepublishing.status AS publishingstatus 
    FROM 
    packagepublishing
    INNER JOIN
        binarypackage ON
            packagepublishing.binarypackage = binarypackage.id
    INNER JOIN
        build ON
            binarypackage.build = build.id
    INNER JOIN
        sourcepackagerelease ON 
            build.sourcepackagerelease = sourcepackagerelease.id
    INNER JOIN
        sourcepackagename ON 
            sourcepackagerelease.sourcepackagename = sourcepackagename.id
    INNER JOIN
        binarypackagefile ON
            binarypackagefile.binarypackage = binarypackage.id
    INNER JOIN
        libraryfilealias ON
            binarypackagefile.libraryfile = libraryfilealias.id
    INNER JOIN
        distroarchrelease ON
            packagepublishing.distroarchrelease = distroarchrelease.id
    INNER JOIN
        distrorelease ON
            distroarchrelease.distrorelease = distrorelease.id
    INNER JOIN
        component ON
            packagepublishing.component = component.id
    ;


-- SourcePackageFilePublishing

DROP VIEW sourcepackagefilepublishing;

CREATE VIEW sourcepackagefilepublishing AS
    SELECT 
        (((libraryfilealias.id)::text || '.'::text) || (sourcepackagepublishing.id)::text) AS id, 
        distrorelease.distribution, 
        sourcepackagepublishing.id AS sourcepackagepublishing, 
        sourcepackagereleasefile.libraryfile AS libraryfilealias, 
        libraryfilealias.filename AS libraryfilealiasfilename, 
        sourcepackagename.name AS sourcepackagename, 
        component.name AS componentname, 
        distrorelease.name AS distroreleasename, 
        sourcepackagepublishing.status AS publishingstatus 
    FROM 
    sourcepackagepublishing
    INNER JOIN
        sourcepackagerelease ON
            sourcepackagepublishing.sourcepackagerelease = 
                sourcepackagerelease.id
    INNER JOIN
        sourcepackagename ON
            sourcepackagerelease.sourcepackagename = sourcepackagename.id
    INNER JOIN
        sourcepackagereleasefile ON
            sourcepackagereleasefile.sourcepackagerelease = 
                sourcepackagerelease.id
    INNER JOIN
        libraryfilealias ON
            libraryfilealias.id = sourcepackagereleasefile.libraryfile
    INNER JOIN
        distrorelease ON
            sourcepackagepublishing.distrorelease = distrorelease.id
    INNER JOIN
        component ON
            sourcepackagepublishing.component = component.id
    ;


-- remove dependencies on SourcePackage table

ALTER TABLE SourcePackageRelease DROP COLUMN sourcepackage;

-- Drop no longer required tables.
DROP TABLE ProductBugAssignment;

DROP TABLE SourcePackageBugAssignment;

DROP TABLE SourcePackageLabel;

DROP TABLE SourcePackageRelationship;

DROP TABLE SourcePackage;

-- set the database revision
INSERT INTO LaunchpadDatabaseRevision VALUES (11, 13, 0);
