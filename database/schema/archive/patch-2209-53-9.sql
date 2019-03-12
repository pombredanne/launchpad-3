-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX binarypackagepublishinghistory__archive__datecreated__id__idx
    ON binarypackagepublishinghistory (archive, datecreated, id);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 53, 9);
