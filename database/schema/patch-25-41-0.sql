
set client_min_messages=ERROR;

CREATE TABLE DistributionSourcePackageCache (
  id                 serial PRIMARY KEY,
  distribution       integer NOT NULL CONSTRAINT
                     distributionsourcepackagecache_distribution_fk
                     REFERENCES Distribution(id),
  sourcepackagename  integer NOT NULL CONSTRAINT
                     distributionsourcepackagecache_sourcepackagename_fk
                     REFERENCES SourcePackageName(id),
  name               text,
  binpkgnames        text,
  binpkgsummaries    text,
  binpkgdescriptions text
);

ALTER TABLE DistributionSourcePackageCache ADD CONSTRAINT
  distributionsourcepackagecache_distribution_sourcepackagename_uniq UNIQUE
  (distribution, sourcepackagename);

CREATE TABLE DistroReleasePackageCache (
  id                 serial PRIMARY KEY,
  distrorelease      integer NOT NULL CONSTRAINT
                     distroreleasepackagecache_distrorelease_fk
                     REFERENCES DistroRelease(id),
  binarypackagename  integer NOT NULL CONSTRAINT
                     distroreleasepackagecache_binarypackagename_fk
                     REFERENCES BinaryPackageName(id),
  name               text,
  summary            text,
  description        text,
  summaries          text,
  descriptions       text
);

ALTER TABLE DistroReleasePackageCache ADD CONSTRAINT
  distroreleasepackagecache_distrorelease_binarypackagename_uniq UNIQUE
  (distrorelease, binarypackagename);

ALTER TABLE BinaryPackageRelease
    ADD COLUMN datecreated timestamp without time zone;
ALTER TABLE BinaryPackageRelease ALTER COLUMN datecreated
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
UPDATE BinaryPackageRelease SET datecreated=DEFAULT WHERE datecreated IS NULL;
ALTER TABLE BinaryPackageRelease ALTER COLUMN datecreated SET NOT NULL;

-- rid ourselves of unused views
DROP VIEW vsourcepackageindistro ;
DROP VIEW vsourcepackagereleasepublishing ;

/* indicate whether a distroarchrelease is official or not */

ALTER TABLE DistroArchRelease ADD COLUMN official boolean;
UPDATE DistroArchRelease SET official=TRUE;
ALTER TABLE DistroArchRelease ALTER COLUMN official SET NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (25,41,0);

