-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX sourcepackagepublishinghistory__archive__spn__status__idx
    ON sourcepackagepublishinghistory (archive, sourcepackagename, status);
CREATE INDEX binarypackagepublishinghistory__archive__bpn__status__idx
    ON binarypackagepublishinghistory (archive, binarypackagename, status);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 53, 5);
