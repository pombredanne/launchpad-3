-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX distributionsourcepackagecache__sourcepackagename__archive__idx
    ON DistributionSourcePackageCache (sourcepackagename, archive);
CREATE INDEX distroseriespackagecache__binarypackagename__archive__idx
    ON DistroSeriesPackageCache (binarypackagename, archive);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 78, 2);
