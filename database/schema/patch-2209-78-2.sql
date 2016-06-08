-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX distributionsourcepackagecache__sourcepackagename__archive__idx
    ON DistributionSourcePackageCache (sourcepackagename, archive);
CREATE INDEX distroseriespackagecache__binarypackagename__archive__idx
    ON DistroSeriesPackageCache (binarypackagename, archive);

CREATE INDEX distributionsourcepackagecache__binpkgnames__idx
    ON DistributionSourcePackageCache USING gin (binpkgnames trgm.gin_trgm_ops);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 78, 2);
