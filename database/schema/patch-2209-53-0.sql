-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX sourcepackagepublishinghistory__datecreated__id__idx
    ON sourcepackagepublishinghistory (datecreated, id);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 53, 0);
