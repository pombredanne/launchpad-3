SET client_min_messages=ERROR;

-- Create new Table

CREATE TABLE Maintainership (
    id                  serial PRIMARY KEY,
    distrorelease       integer NOT NULL
                        CONSTRAINT maintainership_distrorelease_fk
                        REFERENCES DistroRelease(id),
    sourcepackagename   integer NOT NULL
                        CONSTRAINT maintainership_sourcepackagename_fk
                        REFERENCES SourcePackageName(id),
    maintainer          integer NOT NULL
                        CONSTRAINT maintainership_maintainer_fk
                        REFERENCES Person(id)
);


COMMENT ON TABLE Maintainership IS 'Stores the maintainer information for a sourcepackage in a particular distrorelease.';

COMMENT ON COLUMN Maintainership.maintainer IS 'Refers to the person responsible for this sourcepackage inside this distrorelease.';


-- Alter Tables

-- Packaging

ALTER TABLE Packaging ADD COLUMN sourcepackagename INTEGER;
ALTER TABLE Packaging ADD CONSTRAINT packaging_sourcepackagename_fk
      FOREIGN KEY (sourcepackagename) REFERENCES SourcePackagename(id);

ALTER TABLE Packaging ADD COLUMN distrorelease INTEGER;
ALTER TABLE Packaging ADD CONSTRAINT packaging_distrorelease_fk
      FOREIGN KEY (distrorelease) REFERENCES DistroRelease(id);

-- SourcePackageRelease

ALTER TABLE SourcepackageRelease ADD COLUMN distrorelease INTEGER ;
ALTER TABLE SourcePackageRelease ADD CONSTRAINT 
	sourcepackagerelease_distrorelease_fk
      	FOREIGN KEY (distrorelease) REFERENCES DistroRelease(id);
ALTER TABLE SourcepackageRelease ADD COLUMN format INTEGER;

COMMENT ON COLUMN SourcePackageRelease.format IS  'The format of this sourcepackage release, e.g. DPKG, RPM, EBUILD, etc.';


-- Sourcesource
ALTER TABLE Sourcesource ADD COLUMN sourcepackagename INTEGER;
ALTER TABLE Sourcesource ADD CONSTRAINT sourcesource_sourcepackagename_fk
      FOREIGN KEY (sourcepackagename) REFERENCES SourcePackagename(id);

ALTER TABLE Sourcesource ADD COLUMN distrorelease INTEGER;
ALTER TABLE Sourcesource ADD CONSTRAINT sourcesource_distrorelease_fk
      FOREIGN KEY (distrorelease) REFERENCES DistroRelease(id);


-- Alter Views

-- VSourcepackageindistro

-- No ALTER VIEW, so DROP and ADD !!!

DROP VIEW vsourcepackageindistro;

CREATE VIEW vsourcepackageindistro AS
    SELECT DISTINCT 
	sourcepackagerelease.id, 
	sourcepackagerelease.manifest, 
	sourcepackagerelease.format, 
	sourcepackagerelease.sourcepackagename, 
	maintainership.maintainer,
	sourcepackagename.name,
	distrorelease.id AS distrorelease 
	FROM sourcepackagepublishing, 
	     sourcepackagerelease, 
             distrorelease, 
	     maintainership,
	     sourcepackagename
	WHERE 
	-- publishing
	((((sourcepackagepublishing.sourcepackagerelease = 
	    sourcepackagerelease.id) AND 
	-- distrorelease
	   (sourcepackagepublishing.distrorelease = distrorelease.id)) AND
	-- maintainership
	   (maintainership.sourcepackagename = 
	    sourcepackagerelease.sourcepackagename)) AND
	   (maintainership.distrorelease = distrorelease.id))
	ORDER BY 
           sourcepackagename.name, 
           distrorelease.id;

-- VSourcePackageReleasePublishing


-- the same no ALTER VIEW, so ADD and DROP

DROP VIEW vsourcepackagereleasepublishing;

CREATE VIEW vsourcepackagereleasepublishing AS
    SELECT 
	sourcepackagerelease.id, 
	sourcepackagename.name, 
	maintainership.maintainer,
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
	sourcepackagerelease.dsc, 
	sourcepackagerelease.dscsigningkey, 
	distrorelease.id AS distrorelease, 
	component.name AS componentname 
    FROM 
	sourcepackagepublishing, 
	sourcepackagerelease, 
	component, 
	maintainership,
	distrorelease, 
	sourcepackagename 
    WHERE 
	-- publishing
	((((((sourcepackagepublishing.sourcepackagerelease = 
	     sourcepackagerelease.id) AND 
	-- maintainership
	    (maintainership.distrorelease = distrorelease.id)) AND 
	    (maintainership.sourcepackagename = sourcepackagename.id)) AND 
	-- sourcepackagename
	    (sourcepackagerelease.sourcepackagename = sourcepackagename.id)) AND 
	-- distrorelease
            (sourcepackagepublishing.distrorelease = distrorelease.id)) AND 
	-- component
            (component.id = sourcepackagerelease.component))
    ORDER BY
	 sourcepackagename.name, 	
         distrorelease.id;
	

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
	distrorelease, 
	distroarchrelease, 
	processorfamily, 
	packagepublishing, 
	component, 
	section, 
	binarypackage, 
	binarypackagename, 
	build, 
	sourcepackagerelease, 
	sourcepackagename 
     WHERE 
	((((((((((distroarchrelease.distrorelease = distrorelease.id) AND 
	     (distroarchrelease.processorfamily = processorfamily.id)) AND 
	     (distroarchrelease.id = packagepublishing.distroarchrelease)) AND 
	     (packagepublishing.binarypackage = binarypackage.id)) AND 
             (packagepublishing.component = component.id)) AND 
             (packagepublishing.section = section.id)) AND 
             (binarypackage.binarypackagename = binarypackagename.id)) AND 
             (binarypackage.build = build.id)) AND 
             (build.sourcepackagerelease = sourcepackagerelease.id)) AND 
	     (sourcepackagerelease.sourcepackagename = sourcepackagename.id));

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
	sourcepackagepublishing, 
	distrorelease, 
	sourcepackagerelease, 
	sourcepackagename, 
	component, 
	section 
    WHERE 
	(((((sourcepackagepublishing.distrorelease = distrorelease.id) AND 
	(sourcepackagepublishing.sourcepackagerelease = 
	                         sourcepackagerelease.id)) AND 
	(sourcepackagerelease.sourcepackagename = sourcepackagename.id)) AND 
	(sourcepackagepublishing.component = component.id)) AND 
	(sourcepackagepublishing.section = section.id));

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
	packagepublishing, 
	sourcepackagerelease, 
	sourcepackagename, 
	build, 
	binarypackage, 
	binarypackagefile, 
	libraryfilealias, 
	distroarchrelease, 
	distrorelease, 
	component 
    WHERE 
	(((((((((distrorelease.id = distroarchrelease.distrorelease) AND 
	(packagepublishing.distroarchrelease = distroarchrelease.id)) AND 
	(packagepublishing.binarypackage = binarypackage.id)) AND 
	(binarypackagefile.binarypackage = binarypackage.id)) AND 
	(binarypackagefile.libraryfile = libraryfilealias.id)) AND 
	(binarypackage.build = build.id)) AND 
	(build.sourcepackagerelease = sourcepackagerelease.id)) AND 
	(component.id = packagepublishing.component)) AND 
	(sourcepackagename.id = sourcepackagerelease.sourcepackagename));


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
	sourcepackagepublishing, 
	sourcepackagerelease, 
	sourcepackagereleasefile, 
	libraryfilealias, 
	distrorelease, 
	sourcepackagename, 
	component 
    WHERE 
	((((((sourcepackagepublishing.distrorelease = distrorelease.id) AND 
	(sourcepackagepublishing.sourcepackagerelease = 
	                         sourcepackagerelease.id)) AND 
	(sourcepackagereleasefile.sourcepackagerelease = 
	                          sourcepackagerelease.id)) AND 
	(libraryfilealias.id = sourcepackagereleasefile.libraryfile)) AND 
	(sourcepackagerelease.sourcepackagename = sourcepackagename.id)) AND
	(component.id = sourcepackagepublishing.component));


-- Migrate data

-- Populating Maintainership
INSERT INTO Maintainership (distrorelease, sourcepackagename, maintainer)
    SELECT
        distrorelease.id,
        sourcepackage.sourcepackagename,
        sourcepackage.maintainer
    FROM
        sourcepackage JOIN distrorelease ON distrorelease.name='hoary';

-- Repopulating Package
UPDATE Packaging SET sourcepackagename=sourcepackage.sourcepackagename
    FROM SourcePackage WHERE packaging.sourcepackage=SourcePackage.id;
UPDATE Packaging
    SET distrorelease=(SELECT id FROM DistroRelease WHERE name='hoary');
ALTER TABLE packaging DROP COLUMN sourcepackage;


-- Repopulating Sourcepackagerelease

UPDATE SourcePackageRelease
    SET distrorelease=(SELECT id FROM DistroRelease WHERE name='hoary');
UPDATE SourcePackageRelease
    SET format=SourcePackage.srcpackageformat
    FROM SourcePackage
    WHERE SourcePackage.id = SourcePackageRelease.sourcepackage;
ALTER TABLE SourcePackageRelease DROP COLUMN sourcepackage;
ALTER TABLE SourcePackageRelease DROP COLUMN maintainer;
ALTER TABLE SourcePackageRelease ALTER COLUMN format SET NOT NULL;
ALTER TABLE SourcePackageRelease ALTER COLUMN distrorelease SET NOT NULL;


-- Repopulating SourceSource

UPDATE SourceSource
    SET sourcepackagename=SourcePackage.sourcepackagename
    FROM SourcePackage WHERE SourceSource.sourcepackage = SourcePackage.id;
UPDATE SourceSource
    SET distrorelease=(SELECT id FROM DistroRelease WHERE name='hoary');
ALTER TABLE Sourcesource DROP COLUMN sourcepackage;
ALTER TABLE SourceSource ALTER COLUMN distrorelease SET NOT NULL;

-- XXX: So far, all our SourceSource rows have NULL sourcepackage columns
-- so we have no way to populate this. We need to confirm if this really
-- should be NOT NULL, and if so
-- work out where we can initialize the values from.
-- ALTER TABLE SourceSource ALTER COLUMN sourcepackagename SET NOT NULL;


-- Drop no longer required tables.

DROP TABLE SourcePackageBugAssignment;

DROP TABLE SourcePackageLabel;

DROP TABLE SourcePackageRelationship;

DROP TABLE SourcePackage;

