-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

CREATE INDEX binarypackagepublishinghistory__bpn__idx ON BinaryPackagePublishingHistory(bpn);
CREATE INDEX sourcepackagepublishinghistory__spn__idx ON SourcePackagePublishingHistory(spn);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);

