/*
 * Lucille's publishing system needs a few useful views so that it can get on
 * with publishing without performing many skanky SQLObject requests which
 * would slow things down
 */

DROP VIEW SourcePackageFilesToPublish;
CREATE VIEW SourcePackageFilesToPublish AS SELECT
           SourcePackagePublishing.id AS id,
           DistroRelease.distribution AS drd,
SourcePackagePublishing.distrorelease AS sppdrel,
           SourcePackagePublishing.id AS sppid,
          SourcePackageReleaseFile.id AS sprfid,
 SourcePackageReleaseFile.libraryfile AS sprfalias,
    SourcePackageReleaseFile.filetype AS sprftype,
            LibraryFileAlias.filename AS lfaname

FROM SourcePackagePublishing,
     SourcePackageRelease,
     SourcePackageReleaseFile,
     LibraryFileAlias,
     DistroRelease

WHERE SourcePackagePublishing.distrorelease = DistroRelease.id
  AND SourcePackagePublishing.sourcepackagerelease = SourcePackageRelease.id
  AND SourcePackageReleaseFile.sourcepackagerelease = SourcePackageRelease.id
  AND LibraryFileAlias.id = SourcePackageReleaseFile.libraryfile
-- In dbschema.py status of 1 is defined as 'Pending Publishing'
  AND SourcePackagePublishing.status = 1
;
