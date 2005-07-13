/* Add Pocket to views used by publisher */

SET client_min_messages=ERROR;

DROP VIEW binarypackagefilepublishing;
DROP VIEW sourcepackagefilepublishing;

CREATE VIEW binarypackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (packagepublishing.id)::text) AS id, distrorelease.distribution,
    packagepublishing.id AS packagepublishing,
    component.name AS componentname,
    libraryfilealias.filename AS libraryfilealiasfilename,
    sourcepackagename.name AS sourcepackagename,
    binarypackagefile.libraryfile AS libraryfilealias,
    distrorelease.name AS distroreleasename,
    distroarchrelease.architecturetag,
    packagepublishing.status AS publishingstatus,
    packagepublishing.pocket AS pocket
FROM 
    packagepublishing JOIN binarypackage
        ON packagepublishing.binarypackage = binarypackage.id
    JOIN build ON binarypackage.build = build.id
    JOIN sourcepackagerelease
        ON build.sourcepackagerelease = sourcepackagerelease.id
    JOIN sourcepackagename
        ON sourcepackagerelease.sourcepackagename = sourcepackagename.id
    JOIN binarypackagefile
        ON binarypackagefile.binarypackage = binarypackage.id
    JOIN libraryfilealias
        ON binarypackagefile.libraryfile = libraryfilealias.id
    JOIN distroarchrelease
        ON packagepublishing.distroarchrelease = distroarchrelease.id
    JOIN distrorelease
        ON distroarchrelease.distrorelease = distrorelease.id
    JOIN component ON packagepublishing.component = component.id;

CREATE INDEX binarypackagefile_libraryfile_idx
    ON BinaryPackageFile(libraryfile);
CREATE INDEX sourcepackagerelease_sourcepackagename_idx
    ON SourcePackageRelease(sourcepackagename);
CREATE INDEX binarypackagefile_binarypackage_idx
    ON BinaryPackageFile(binarypackage);

CREATE VIEW sourcepackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (sourcepackagepublishing.id)::text) AS id,
    distrorelease.distribution,
    sourcepackagepublishing.id AS sourcepackagepublishing,
    sourcepackagereleasefile.libraryfile AS libraryfilealias,
    libraryfilealias.filename AS libraryfilealiasfilename,
    sourcepackagename.name AS sourcepackagename,
    component.name AS componentname,
    distrorelease.name AS distroreleasename,
    sourcepackagepublishing.status AS publishingstatus,
    sourcepackagepublishing.pocket AS pocket
FROM 
    sourcepackagepublishing
    JOIN sourcepackagerelease ON 
        sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id
    JOIN sourcepackagename
        ON sourcepackagerelease.sourcepackagename = sourcepackagename.id
    JOIN sourcepackagereleasefile
        ON sourcepackagereleasefile.sourcepackagerelease
        = sourcepackagerelease.id
    JOIN libraryfilealias
        ON libraryfilealias.id = sourcepackagereleasefile.libraryfile
    JOIN distrorelease
        ON sourcepackagepublishing.distrorelease = distrorelease.id
    JOIN component ON sourcepackagepublishing.component = component.id;

CREATE INDEX sourcepackagereleasefile_sourcepackagerelease_idx
    ON SourcePackageReleaseFile (SourcePackageRelease);
CREATE INDEX sourcepackagereleasefile_libraryfile_idx
    ON SourcePackageReleaseFile (libraryfile);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 27, 0);
