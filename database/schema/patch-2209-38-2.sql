-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX upload_archive__upload_distroseries__sourcepackagename__idx
  ON latestpersonsourcepackagereleasecache (upload_archive, upload_distroseries, sourcepackagename);


INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 38, 2);
