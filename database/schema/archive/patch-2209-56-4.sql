-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX livefsfile__libraryfile__idx ON livefsfile(libraryfile);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 56, 4);
