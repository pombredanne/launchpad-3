-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX sourcepackagepublishinghistory__packageupload__idx_2
    ON sourcepackagepublishinghistory (packageupload);
CREATE INDEX binarypackagepublishinghistory__supersededby__idx
    ON binarypackagepublishinghistory (supersededby);
CREATE INDEX binarypackagereleasedownloadcount__binary_package_release__idx
    ON binarypackagereleasedownloadcount (binary_package_release);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 53, 3);
