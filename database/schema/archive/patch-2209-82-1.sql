-- Copyright 2017 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX sourcepackagerelease__buildinfo__idx
    ON SourcePackageRelease (buildinfo);
CREATE INDEX binarypackagebuild__buildinfo__idx
    ON BinaryPackageBuild (buildinfo);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 82, 1);
