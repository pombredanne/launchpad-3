-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX sourcepackagepublishinghistory__archive__status__deleted__idx
    ON sourcepackagepublishinghistory (archive, status)
    WHERE scheduleddeletiondate IS NULL AND dateremoved IS NULL;

CREATE INDEX binarypackagepublishinghistory__archive__status__deleted__idx
    ON binarypackagepublishinghistory (archive, status)
    WHERE scheduleddeletiondate IS NULL AND dateremoved IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 53, 8);
